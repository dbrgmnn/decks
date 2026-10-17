# decks

Minimal flashcards app with folders, decks, cards, and FSRS-based study.

## Run with Docker

```bash
./deploy.sh          # build and start
./deploy.sh pull     # pull latest code and deploy
./deploy.sh restart  # rebuild and restart
./deploy.sh logs     # follow logs
./deploy.sh down     # stop
```

Serves on port `9000`. Runtime data (SQLite) lives in `./data` — copy it to
back up or move the app. Open `http://SERVER_IP:9000`.

## License

MIT License. See `LICENSE`.
