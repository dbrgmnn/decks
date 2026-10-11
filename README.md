# decks

Minimal flashcards app with folders, decks, cards, and FSRS-based study.

## Run locally

```bash
python3.12 -m venv .venv
. .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --host 0.0.0.0 --port 9000
```

Open `http://127.0.0.1:9000` on the same machine.
If you run the app on another device or server, open `http://SERVER_IP:9000` instead.

## Deploy with Docker

Build and start the container from the current local code:

```bash
./deploy.sh
```

Pull the latest code and deploy:

```bash
./deploy.sh pull
```

Other useful commands:

```bash
./deploy.sh logs
./deploy.sh restart
./deploy.sh down
```

The Docker setup publishes port `9000` and mounts `./data` into the container at `/app/data`.
Open `http://127.0.0.1:9000` if Docker runs on your current machine, or `http://SERVER_IP:9000` if it runs on a server.

## Data

All runtime data is stored in `data/`, including the SQLite database file.
Copy this folder to back up or move the app.

## Requirements

- Local run: Python 3.12+
- Docker deploy: Docker
- `./deploy.sh pull`: Docker and Git

## License

MIT License. See `LICENSE`.
