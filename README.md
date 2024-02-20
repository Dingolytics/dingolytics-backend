Dingolytics backend
===================

This is a server-side of the Dingolytics application. For deployment
instructions, check the [dingolytics-selfhosted](https://github.com/Dingolytics/dingolytics-selfhosted) repository and for the front-end part, check the [dingolytics](https://github.com/Dingolytics/dingolytics) repository.

![Docker Image Size (latest by date)](https://img.shields.io/docker/image-size/dingolytics/redash-wild-server?sort=date)


Development
-----------

The easiest way to start development is to use Docker Compose. Before
starting, you need to create a `.env` file, check the `env.template`
for the reference.

Start the server with:

```bash
docker-compose up --build
```

Run tests:

```bash
make test
```

or selectively:

```bash
TEST_ARGS='-x dingolytics/' make test
```


Credits to Redash
-----------------

Our project involves forking [Redash](https://redash.io) with the intention of
improving it and creating a new product, with a different focus.

We extracted back-end part to build and deploy separately.
HTTP API level compatibility is a mid-term goal to keep because
it is used by the front-end part.

The more project evolves, the more divergent it becomes from the original.

- Dependencies are updated to the latest versions
- PostgreSQL of version 15.x is used
- Database migrations history is cleaned up to start from scratch
- `PseudoJSON` field removed in favor of `JSONB`
- SQLAlchemy is updated to the latest version, queries updated
- Disabled changes tracking via `ChangeTrackingMixin`
- Release management scripts are removed, to reconsider later

Check the **LICENSE.redash** file for the original license.


License
-------

This repository contains a forked version of Redash <https://redash.io>,
which is licensed under the BSD-2-Clause license.

This forked repository includes modifications made by Dingolytics team,
which are also licensed under the BSD-2-Clause license.

Dingolytics team:

- Alexey Kinev <https://github.com/rudyryk>
- Ekaterina Ponomarenko <https://github.com/alesten-code>
