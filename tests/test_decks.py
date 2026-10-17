def test_deck_delete_targets_the_edited_deck(client):
    # The delete button must use the deck shown in the edit sheet, never the last
    # deck whose cards were opened, or it can delete the wrong deck.
    source = client.get("/static/modules/decks.js").text
    assert "getCurrentDeck" not in source
    assert "deckEditSheet.dataset.deckId" in source
