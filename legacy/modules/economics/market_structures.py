def classify_market(structure):
    description = {
        "Perfect Competition": 
            "Many firms, No pricing power",
        "Monopoly": 
            "Single seller with market power",
        "Oligopoly":
            "Few firms with strong competition.",
        "Monopolistic Competition":
            "Many firms with differentiated products.",

    }

    return description.get(
        structure,
        "Unknown structure"
    )
