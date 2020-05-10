=====================
graphene-peewee
=====================

This is an early port of `graphene-peewee-async <https://github.com/insolite/graphene-peewee-async>`_ for use with the regular, synchronous `peewee ORM <https://github.com/coleifer/peewee>`_. All asynchronous code has been removed, as well as code related to `peewee-async <https://github.com/05bit/peewee-async>`_. 

This release also contains various minor bug fixes and improvements, including proper deserialization of timestamp fields, compatibility with databases initialized as Proxy objects, removal of various Postgres-specific features such as RETURNING so that other databases like MySQL and SQLite3 can be used, and a few other, minor bug fixes.

Several new unit tests have been added, and they've been changed to use the in-memory SQLite3 database instead of Postgres.

Since this is an early release, it has undergone limited testing and usage. Additional testers would be highly appreciated.

Major credit to `insolite <https://github.com/insolite>`_ for developing `graphene-peewee-async <https://github.com/insolite/graphene-peewee-async>`_.
