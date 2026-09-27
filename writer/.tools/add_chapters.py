#!/usr/bin/env python3
"""
Reusable "add chapters" tool.

Appends new chapter entries to a poetry book's backlog book.json and pipeline
book.json, and reconciles model.json, bookseed.txt, progress.json, and the
chapter folders. New chapters are defined inline in NEW_CHAPTERS below.

Usage:
    python .tools/add_chapters.py <bookname>
"""
import json
import os
import sys

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))

# (title, summary) pairs for the new chapters. Edit this list to add chapters.
NEW_CHAPTERS = [
    ("The Tethys Sea", "The ancient sea that once covered this plain still laps at the city's foundations. The context turns on the water that was here before the land."),
    ("The Gondwana Drift", "The continent that drifted and broke still moves beneath the city. The context turns on the slow migration written in stone."),
    ("The Quartzite Vein", "The quartzite that runs through the Ridge is the earth's oldest blood. The context turns on the mineral that outlasts every empire."),
    ("The Schist and the Sky", "The schist of the Aravalli holds the memory of a sky that had no name. The context turns on the stone that remembers the first light."),
    ("The Badarpur Quarries", "The ancient bedrock is ground down to build modern apartments. The context turns on the mountain that becomes a wall."),
    ("The Asola Bhatti Lakes", "Water fills the craters left by mining, and leopards rule the night. The context turns on the wildness that returns to the wound."),
    ("The Manger Jungle", "Wild boars and secret lovers share the oldest forest. The context turns on the green that hides what the city cannot see."),
    ("The Ridge's Green Breath", "The half-dead heart of the city still breathes through its trees. The context turns on the pulse that refuses to stop."),
    ("The Peacocks of Raisina", "Wild peacocks walk beside the seat of power. The context turns on the beauty that ignores the throne."),
    ("The Anangpur Dam", "Eighth-century water engineering hides in the scrubland. The context turns on the water that was tamed before the city was named."),
    ("The Sultan Ghari Crypt", "The hidden crypt of the first slave-king's forgotten son. The context turns on the dead who are buried before the dynasty is born."),
    ("The Yogmaya Shrine", "An older sacred space predating the Sultanate. The context turns on the goddess who was here before the kings."),
    ("The Tomar Forts", "The first stone builders, forgotten by almost everyone. The context turns on the founders whose names the city lost."),
    ("The Lalkot Walls", "Prithviraj's walls still stand in the scrub. The context turns on the last Hindu king's unfinished defence."),
    ("The Qutub's Shadow", "Seventy-three metres of conquest carved with verses. The context turns on the stone that reaches for a sky it cannot hold."),
    ("The Siri Fort's Silence", "Alauddin's military arrogance flattened into a morning park. The context turns on the war that became a lawn."),
    ("The Feroz Shah Kotla", "Djinns live among broken pillars and cricket cheers. The context turns on the spirits that outlast the stones."),
    ("The Humayun's Tomb", "Persian symmetry masking a clumsy emperor's bones. The context turns on the beauty that hides the fall."),
    ("The Safdarjung Whisper", "The last Mughal whisper, forgotten in a generation. The context turns on the empire that ended in a garden."),
    ("The Jama Masjid's Crowd", "Twenty-five thousand worshippers inside, chaos outside. The context turns on the prayer that holds against the noise."),
    ("The Khirki Masjid", "A fortress-mosque whose stone windows catch no breeze. The context turns on the prayer that cannot breathe."),
    ("The Adham Khan's Dome", "The haunted dome of a murderer punished by his emperor. The context turns on the justice that outlives the crime."),
    ("The Jamali Kamali", "Sufi saints and hidden whispers in red sandstone. The context turns on the secret that the stone keeps."),
    ("The Ghalib's Haveli", "Poetry born in poverty in Ballimaran. The context turns on the verse that survived the hunger."),
    ("The Chandni Chowk", "Chaos perfected — eat, pray, buy, survive. The context turns on the market that never sleeps."),
    ("The Khari Baoli", "The spice market where the air burns the throat. The context turns on the scent that is older than the city."),
    ("The Kinari Bazaar", "Tinsel and gold lace sold by the kilo. The context turns on the joy that is bought and worn."),
    ("The Chawri Bazaar", "Once nautch girls, now brass paper rolls. The context turns on the street that changed its song."),
    ("The Fatehpuri Steps", "Old men watch the pigeons scatter in the afternoon sun. The context turns on the stillness inside the crowd."),
    ("The Daryaganj Books", "Knowledge sold on dusty plastic sheets. The context turns on the words that cost almost nothing."),
    ("The Kashmere Gate", "Bullet-riddled stones remembering 1857. The context turns on the wall that still bleeds."),
    ("The North and South Blocks", "Twin monoliths dictating files and destinies. The context turns on the power that lives in stone."),
    ("The India Gate Names", "Dead soldiers' names carved in stone, ignored by picnickers. The context turns on the memory that no one reads."),
    ("The Connaught Place", "A white colonial horseshoe trapping greed and youth. The context turns on the circle that holds the city."),
    ("The Lodhi Gardens", "Joggers step over royal graves. The context turns on the kings who became a path."),
    ("The Agrasen ki Baoli", "A stepwell dropping into the earth, holding shadows instead of water. The context turns on the depth that forgot its water."),
    ("The Yamuna at Wazirabad", "The sacred river meets industrial foam before it enters the town. The context turns on the holiness that is poisoned at the gate."),
    ("The Najafgarh Drain", "The concrete creek carrying the hidden waste of millions. The context turns on the river that became a sewer."),
    ("The Hauz Khas Tank", "A dry medieval reservoir reflecting upscale cafes. The context turns on the water that became a mirror for wine."),
    ("The Okhla Barrage", "The river chained by locks, gates, and pipes. The context turns on the water that is held against its will."),
]


def add_chapters(bookname: str) -> None:
    BOOK = bookname
    BACKLOG = os.path.join(ROOT, ".space", "backlog", BOOK)
    PIPE = os.path.join(ROOT, ".space", "pipeline", BOOK)

    backlog_path = os.path.join(BACKLOG, "book.json")
    with open(backlog_path, encoding="utf-8") as f:
        plan = json.load(f)

    existing = plan["chapters"]
    start = max(c["chapter_index"] for c in existing) + 1

    new_entries = []
    for i, (title, summary) in enumerate(NEW_CHAPTERS):
        idx = start + i
        new_entries.append({
            "chapter_index": idx,
            "name": str(idx),
            "word_target": 500,
            "chapter_title": title,
            "chapter_summary": summary,
            "further_references": [],
        })

    plan["chapters"].extend(new_entries)
    plan["chapter_count"] = len(plan["chapters"])

    with open(backlog_path, "w", encoding="utf-8") as f:
        json.dump(plan, f, indent=2, ensure_ascii=False)

    # pipeline book.json (clone)
    pipe_book = os.path.join(PIPE, "book.json")
    if os.path.exists(pipe_book):
        with open(pipe_book, "w", encoding="utf-8") as f:
            json.dump(plan, f, indent=2, ensure_ascii=False)

    # book.json (the cloned plan; fall back to legacy model.json)
    model_path = os.path.join(PIPE, "book.json")
    if not os.path.exists(model_path):
        model_path = os.path.join(PIPE, "model.json")
    if os.path.exists(model_path):
        with open(model_path, encoding="utf-8") as f:
            model = json.load(f)
        model["chapter_count"] = len(plan["chapters"])
        model["source_terms"] = [c["chapter_title"] for c in plan["chapters"]]
        with open(model_path, "w", encoding="utf-8") as f:
            json.dump(model, f, indent=2, ensure_ascii=False)

    # bookseed.txt
    seed_path = os.path.join(PIPE, "bookseed.txt")
    with open(seed_path, "w", encoding="utf-8") as f:
        for c in plan["chapters"]:
            f.write(c["chapter_title"] + "\n")

    # progress.json
    prog_path = os.path.join(PIPE, "progress.json")
    if os.path.exists(prog_path):
        with open(prog_path, encoding="utf-8") as f:
            prog = json.load(f)
        prog["total_chapters"] = len(plan["chapters"])
        prog["source_terms"] = [c["chapter_title"] for c in plan["chapters"]]
        existing_nums = {c["chapter_number"] for c in prog["chapters"]}
        for e in new_entries:
            if e["chapter_index"] not in existing_nums:
                prog["chapters"].append({
                    "chapter_number": e["chapter_index"],
                    "topic": e["chapter_title"],
                    "category": "The Woman Who Is Delhi",
                    "status": "pending",
                    "file_path": f"chapters\\{e['chapter_index']}\\chapter.md",
                    "completed_date": None,
                })
        with open(prog_path, "w", encoding="utf-8") as f:
            json.dump(prog, f, indent=2, ensure_ascii=False)

    # chapter folders
    chapters_dir = os.path.join(PIPE, "chapters")
    for e in new_entries:
        n = e["chapter_index"]
        cd = os.path.join(chapters_dir, str(n))
        os.makedirs(os.path.join(cd, "history"), exist_ok=True)
        seg = os.path.join(cd, "segments", "1")
        os.makedirs(os.path.join(seg, "writer"), exist_ok=True)
        os.makedirs(os.path.join(seg, "editor"), exist_ok=True)
        os.makedirs(os.path.join(seg, "translator"), exist_ok=True)

        cm = {
            "level": "chapter",
            "state": "scaffolded",
            "chapter_index": n,
            "chapter_name": str(n),
            "topic": e["chapter_title"],
            "chapter_title": e["chapter_title"],
            "chapter_summary": e["chapter_summary"],
            "word_target": 500,
            "segments": [1],
        }
        with open(os.path.join(cd, "chapter.json"), "w", encoding="utf-8") as f:
            json.dump(cm, f, indent=2, ensure_ascii=False)

        sm = {"level": "segment", "state": "returning", "chapter_index": n, "segment_index": 1}
        with open(os.path.join(seg, "model.json"), "w", encoding="utf-8") as f:
            json.dump(sm, f, indent=2, ensure_ascii=False)

        with open(os.path.join(cd, "chapter.md"), "w", encoding="utf-8") as f:
            f.write(f"# {e['chapter_title']}\n\n{e['chapter_summary']}\n")

    print(f"Added {len(new_entries)} chapters ({start}-{start + len(new_entries) - 1}) to {BOOK}. Total now {len(plan['chapters'])}.")


if __name__ == "__main__":
    if len(sys.argv) != 2:
        sys.exit("Usage: python .tools/add_chapters.py <bookname>")
    add_chapters(sys.argv[1])
