## Integration tests (starter)

This folder is a placeholder for docker-compose based integration tests.

Typical approach:

- bring up `docker compose -f docker-compose.yml up -d`
- run `pytest -m integration`
- test flows:
  - register/login
  - create chip + validate
  - simulate RFID scan + observe access decision events
  - simulate card payment webhook + recharge

