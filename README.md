Redash (wild edition) server
============================

![Docker Image Size (latest by date)](https://img.shields.io/docker/image-size/dingolytics/redash-wild-server?sort=date)

This is a "wild" fork of [Redash](https://redash.io) project:  

- Extracted back-end part to build and deploy separately
- HTTP API level compatibility is a goal
- Codebase backwards compatibility is not a goal


Changes overview
----------------

- Dependencies are updated to the latest versions
- PostgreSQL of version 15.x is used
- Database migrations history is cleaned up to start from scratch
- `PseudoJSON` field removed in favor of `JSONB`
- SQLAlchemy is updated to the latest version, queries updated
- Disabled changes tracking via `ChangeTrackingMixin`
- Release management scripts are removed, to reconsider later


Development
-----------

The easiest way to start development is to use Docker Compose. Before
starting, you need to create a `.env` file with the following contents:

```bash
# Generate secrets with `openssl rand -hex 32` or use random strings
REDASH_COOKIE_SECRET=...
REDASH_SECRET_KEY=...
```

Then creare a database tables with:

```bash
docker-compose run --rm server create_tables
```

Finally, start the server with:

```bash
docker-compose up --build
```

Run tests:

```bash
make test
```

or selectiely:

```bash
docker-compose -f docker-compose.tests.yml run --rm server tests tests/models
```


TODO
----

Short-term tasks:

- [x] Restore tests and CI
- [ ] Stream model to connect [Vector](https://vector.dev) with data sources
  - [x] Auto-create ClickHouse table after Stream creation
  - [ ] Auto-create Vector source after Stream creation
- [ ] Use modern password hashing algorithms
- [ ] Re-implement versioning for `Query` model
- [ ] Re-implement saving results logic, `QueryResult` model
- [x] Reduce Docker image size for release builds


Credits
-------

In summary, our project involves forking Redash with the intention of
improving it and creating a new product. We value the original work and
aim to appreciate and contribute to it while also developing our own
unique vision.

When forking an original work, it is important to appreciate the effort and
value of the original creators while also acknowledging the need for changes
and improvements. We believe that the best way to do this is to be transparent
about our intentions and to give credit to the original creators
and contributors.

Our approach involves collaborating with the Redash community to contribute
back to the original project if possible while also maintaining a separate
codebase for our own project. 

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
