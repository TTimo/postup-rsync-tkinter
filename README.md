# Introduction

Trigger an rsync update at the end of a TortoiseSVN get or a git checkout with TkInter GUI.

This demonstrates how to configure a post update client side hook in TortoiseSVN to execute a script of your choice (https://tortoisesvn.net/docs/release/TortoiseSVN_en/tsvn-dug-settings.html#tsvn-dug-settings-hooks). It can also be used with a git hook (https://git-scm.com/docs/githooks).

# Installation

The script can be packaged to run standalone with pyinstaller.

For development you will need the signalslot library: https://pypi.python.org/pypi/signalslot

# Unit Tests

Some basic tests are provided:

ttimo_000@VANGUARD C:/D/tkinter-svn-postup-rsync> /cygdrive/c/Python27/python.exe -m unittest -v postup
test (postup.CallableTest) ... ok
test (postup.ExecutorTest) ... ok

# Standalone packaging

Produce a standalone .exe using pyinstaller (http://www.pyinstaller.org/):

pyinstaller.exe --windowed -y postup.py

# Rsync

https://www.itefix.net/cwrsync

# Configuration

Example configuration for TortoiseSVN:

![TortoiseSVN post update property](tortoisesvn-postup.png "Title")

Similar configuration for Git is left as an exercise to the reader.
