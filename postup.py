# use pyinstaller to make a standalone. package this with the following options:
# postup_source> pyinstaller.exe --windowed -y postup.py
# no point showing the DOS console, we can't print anything to it for some reason

# -- builtin modules --
import sys
import os
import time
import pprint
import threading
import Queue
import subprocess
import unittest
import Tkinter as tk
import logging
logging.basicConfig( filename = 'postup.log', level = logging.DEBUG )

# -- extra --
# svn> /cygdrive/c/Python27/Scripts/pip.exe install weakrefmethod
# svn> /cygdrive/c/Python27/Scripts/pip.exe install signalslot
import signalslot

# -- configuration --
RSYNC_BIN_PATH = r'cwRsync_5.4.1_x86_Free\rsync.exe'
RSYNC_PASSWORD_FILE = 'password.txt'

# Point to your rsync server: RSYNC_URL = 'rsync://login@host/path'
RSYNC_URL = None
RSYNC_PASS = None

# Basic settings
AUTOCLOSE_SETTING = 'autoclose.setting'
FORK_SETTING = 'fork.setting'

# So you can spin a process and watch it's output as execution progresses
# See http://stackoverflow.com/questions/375427/non-blocking-read-on-a-subprocess-pipe-in-python
class Executor( threading.Thread ):
    def __init__( self, cmd ):
        super( Executor, self ).__init__()
        self.daemon = True
        self.cmd = cmd
        self.out = Queue.Queue()
        self.p = None

    def run( self ):
        self.p = subprocess.Popen( self.cmd, shell = True, stdout = subprocess.PIPE, bufsize = 1 )
        for line in iter( self.p.stdout.readline, b'' ):
            self.out.put( line )
        self.p.stdout.close()

# postup_source> /cygdrive/c/Python27/python.exe -m unittest postup
class ExecutorTest( unittest.TestCase ):
    def test( self ):
        e = Executor( [ r'ping.exe', '-n', '3', '8.8.8.8' ] )
        e.start()
        while ( e.is_alive() ):
            try:
                line = e.out.get( timeout = .1 )
            except Queue.Empty:
                pass
            else:
                logging.info( line )

# A more simple version that sends all output to python logging
# Then we just pipe all logging output to the Tk UI
class LoggingExecutor( threading.Thread ):
    def __init__( self, cmd ):
        super( LoggingExecutor, self ).__init__()
        self.daemon = True
        self.cmd = cmd
        self.p = None
        self.do_terminate = False

        self.signal_done = signalslot.Signal( args = [ 'success', ] )

    def run( self ):
        success = False
        try:
            #raise Exception( 'boo' )
            # NOTE: shell = True makes the rsync.exe DOS box not show, no use otherwise
            self.p = subprocess.Popen( self.cmd, stdout = subprocess.PIPE, bufsize = 1, shell = True )
            for line in iter( self.p.stdout.readline, b'' ):
                logging.info( line.strip('\n') )
                if ( self.do_terminate ):
                    # NOTE: Does not work well with slow output since we wait on a printed line.
                    # Will break completely on a silent process.
                    # Would need some kind of timeout cycle to improve on this.
                    self.p.terminate()
                    break
            self.p.stdout.close()
            ret = self.p.wait()
            success = ( ret == 0 )
        except Exception as e:
            logging.info( 'Exception:' )
            logging.error( e, exc_info = True )
            success = False
        finally:
            self.signal_done.emit( success = success )

    def terminate( self ):
        # Issuing terminate from a different thread does not work reliably (or at all)
        self.do_terminate = True

class LoggingExecutorTest( unittest.TestCase ):
    def test( self ):
        e = LoggingExecutor( [ r'ping.exe', '-n', '3', '8.8.8.8' ] )
        e.start()
        while ( e.is_alive() ):
            time.sleep( .1 )

class CallableTest( unittest.TestCase ):
    def test( self ):
        # just because the syntax of those things sometimes confuses me :)
        def _call( msg ):
            print( '_call %s' % msg )
        print( 'create callable' )
        cl = lambda : _call( 'hay' )
        print( 'call' )
        cl()

class ProgressUI( object ):
    def __init__( self ):
        # -- dependency injection --
        self.parent = None

        # -- state --
        self.frame_top = None
        self.label_messages = None
        self.exec_queue = None

    def setup( self ):
        self.exec_queue = Queue.Queue()
        
        self.frame_top = tk.Frame( self.parent )
        self.frame_top.pack()

        self.text_messages = tk.Text( self.frame_top )
        self.text_messages.pack()

        self.button = tk.Button( self.frame_top, text = 'Abort' )        
        self.button.pack( side = tk.RIGHT )
        self.button.bind( '<Button-1>', self._onClick )

        self.fork_var = tk.IntVar()
        self.fork_var.set( os.path.exists( FORK_SETTING ) )
        self.fork_var.trace( 'w', self._onToggleFork )
        self.fork = tk.Checkbutton( self.frame_top, text = 'Fork', variable = self.fork_var )
        self.fork.pack( side = tk.RIGHT )
        
        self.autoclose_var = tk.IntVar()
        self.autoclose_var.set( os.path.exists( AUTOCLOSE_SETTING ) )
        self.autoclose_var.trace( 'w', self._onToggleAutoclose )
        self.autoclose = tk.Checkbutton( self.frame_top, text = 'Auto-close', variable = self.autoclose_var )
        self.autoclose.pack( side = tk.RIGHT )

        self.parent.after_idle( self.pump )

    # we have to run our own loop from the UI thread, because Tk's event scheduler is not thread safe
    # see https://stackoverflow.com/questions/27033804/tkinter-crash-panic-in-call-to-tcl-appendformattoobj/
    def pump( self ):
        # arm it again right away
        # using after_idle causes a stall
        # using a value too low for after causes a stall or freeze also (1 or 2) .. system specific? hugh
        self.parent.after( 5, self.pump )
        while ( not self.exec_queue.empty() ):
            cl = self.exec_queue.get_nowait()
            cl()

    def onLogRecord( self, record, **kwargs ):
        # we are potentially on a thread. create a callable and pass it to the queue
        self.exec_queue.put( lambda : self._addText( record.msg ) )

    def _addText( self, msg ):
        self.text_messages.insert( tk.END, '%s\n' % msg )
        self.text_messages.see( tk.END )

    def onDone( self, success, **kwargs ):
        self.exec_queue.put( lambda : self._onDone( success ) )

    def _onDone( self, success ):
        self._addText( 'Done!' )
        if ( success ):
            self.button['text'] = 'Close'
        else:
            self.button['text'] = 'FAILED'
            self.button['foreground'] = 'red'
        if ( success and self.autoclose_var.get() == 1 ):
            self.parent.quit()

    def _onClick( self, event ):
        logging.info( 'quit/abort button pressed' )
        self.parent.quit()

    def _onToggleAutoclose( self, *args ):
        if ( self.autoclose_var.get() ):
            file( AUTOCLOSE_SETTING, 'a' )
        else:
            if ( os.path.exists( AUTOCLOSE_SETTING ) ):
                os.unlink( AUTOCLOSE_SETTING )

    def _onToggleFork( self, *args ):
        if ( self.fork_var.get() ):
            file( FORK_SETTING, 'a' )
        else:
            if ( os.path.exists( FORK_SETTING ) ):
                os.unlink( FORK_SETTING )
        
class ProgressUITest( unittest.TestCase ):
    def test( self ):
        # just bring it up doing nothing
        root = tk.Tk()
        pui = ProgressUI()
        pui.parent = root
        pui.setup()
        root.mainloop()

class HandlerToUI( logging.Handler ):
    def __init__( self ):
        super( HandlerToUI, self ).__init__()

        # -- signals --
        self.signal_log_record = signalslot.Signal( args = [ 'record', ] )

    def setup( self ):
        logging.root.addHandler( self )
        
    def emit( self, record ):
        self.signal_log_record.emit( record = record )

class TestHandler( unittest.TestCase ):
    def test( self ):
        # prepare the UI
        root = tk.Tk()
        pui = ProgressUI()
        pui.parent = root
        pui.setup()

        # setup a bridge from logging to the UI
        h2ui = HandlerToUI()
        h2ui.setup()
        h2ui.signal_log_record.connect( pui.onLogRecord )        

        # start a process that will send it's output to logging
        e = LoggingExecutor( [ r'ping.exe', '-n', '10', '8.8.8.8' ] )
        e.signal_done.connect( pui.onDone )
        e.start()

        # bring the UI up
        root.mainloop()

if ( __name__ == '__main__' ):
    # we are being executed with cwd as the top of the checkout tree
    logging.debug( 'getcwd: %s' % repr( os.getcwd() ) )

    if ( os.path.exists( FORK_SETTING ) ):
        # fork execution so we don't hold up the Tortoise dialog - only works with the packaged version
        logging.debug( 'sys.argv: %s' % repr( sys.argv ) )
        try:
            sys.argv.index( '--forked' )
        except:
            if ( sys.argv[0][-4:] == '.exe' ):
                logging.info( 'Forking execution %s' % ( repr( sys.argv ) ) )
                args = sys.argv
                args.append( '--forked' )
                os.execv( sys.argv[0], args )
                sys.exit( 0 )
            else:
                logging.info( 'Script run skips fork setting' )
        else:
            logging.info( 'Detected forked execution, continuing.' )
    
    # write out the password to a file for rsync
    if ( not os.path.exists( RSYNC_BIN_PATH ) ):
        logging.info( 'RSYNC NOT FOUND - DEMO MODE' )
        cmd = [ r'ping.exe', 'google.com' ]
    else:
        file( RSYNC_PASSWORD_FILE, 'wb' ).write( RSYNC_PASS )
        cmd = [ RSYNC_BIN_PATH, '--password-file=%s' % RSYNC_PASSWORD_FILE, '-a', '--verbose' ]
        #cmd.append( '--delete' )
        cmd += [ RSYNC_URL, '.' ]
        logging.info( 'Command: %s' % pprint.pformat( cmd ) )

    # prepare the UI object
    root = tk.Tk()
    pui = ProgressUI()
    pui.parent = root
    pui.setup()

    # setup a bridge from logging to the UI
    h2ui = HandlerToUI()
    h2ui.setup()
    h2ui.signal_log_record.connect( pui.onLogRecord )        
    
    # start running the rsync command
    e = LoggingExecutor( cmd )
    e.signal_done.connect( pui.onDone )
    e.start()
    
    # bring up the UI
    root.mainloop()
    logging.info( 'mainloop returns' )

    # kill rsync if still running (user abort)
    while ( e.is_alive() ):
        logging.info( 'terminate process' )
        e.terminate()
        time.sleep( 1 )

    # cleanup
    os.unlink( RSYNC_PASSWORD_FILE )
