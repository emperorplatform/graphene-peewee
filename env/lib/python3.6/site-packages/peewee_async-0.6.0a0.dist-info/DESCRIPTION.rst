Current state: **alpha**, yet API seems fine and mostly stable.

Since version 0.6.0 peewee-async is compatible with peewee 3.5+ and
support of Python 3.4 is dropped.

* Works on Python 3.5+
* Required peewee 3.5+
* Has support for PostgreSQL via `aiopg`
* Has support for MySQL via `aiomysql`
* Single point for high-level async API
* Drop-in replacement for sync code, sync will remain sync
* Basic operations are supported
* Transactions support is present, yet not heavily tested

The source code is hosted on `GitHub`_.

.. _GitHub: https://github.com/05bit/peewee-async


