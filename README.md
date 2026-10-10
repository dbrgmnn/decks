# decks

Minimal flashcards app with folders, decks, cards, and FSRS-based study.

## Run locally

```bash
python3.12 -m venv .venv
. .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --host 0.0.0.0 --port 9000
```

Open `http://127.0.0.1:9000`.

## Deploy with Docker

Deploy the current code on the server:

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

Open `http://127.0.0.1:9000`.

## Data

All runtime data is stored in `data/`.
Copy this folder to back up or move the app.

## License

MIT License. See `LICENSE`.
