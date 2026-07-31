Deployment
==========

Production: Linode VPS (Ubuntu 24.04) via Ansible + Docker Compose.

Pipeline: push → lint+test+pytest(81%) → Docker build+push ghcr.io → deploy.

.. code-block:: bash

   cd infra/ansible
   ansible-playbook deploy.yml -i inventory.yml --limit clickmart-prod
