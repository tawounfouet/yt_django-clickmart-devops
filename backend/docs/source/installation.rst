Installation
============

Prerequisites: Python >= 3.11, Docker, PostgreSQL 16.

Quick Start
-----------

.. code-block:: bash

   cd backend
   uv pip install -r requirements.txt
   python manage.py migrate
   python manage.py runserver

Docker
------

.. code-block:: bash

   docker compose up -d
