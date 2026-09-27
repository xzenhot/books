# Signature Registry

A catalog of every poetry signature available in `poetry/signatures/`. Each signature is a distinct poetic voice — a poet's characteristic movement, motifs, diction, and pattern — that the writer or reframer agent uses to render a chapter in a specific style.

The writer agent reads this registry to discover available signatures, then reads the individual `signature.md` for the full definition.

---

## Available Signatures

| # | Signature | Folder | Voice | Status |
|---|-----------|--------|-------|--------|
| 1 | Kahlil Gibran | `gibran/` | Biblical, aphoristic, oracular | ✅ Active |
| 2 | Marcus Aurelius | `aurilus/` | Meditative, restrained, Stoic | ✅ Active |
| 3 | Jibanananda Das | `jibanananda/` | Twilight-toned, solitary, sensuous | ✅ Active |
| 4 | Rabindranath Tagore (Sangeet) | `rabindrasangeet/` | Songlike, devotional, intimate | ✅ Active |
| 5 | Rumi | `rumi/` | Ecstatic, mystical, intoxicated | ✅ Active |
| 6 | Walt Whitman | `whitman/` | Expansive, democratic, celebratory | ✅ Active |
| 7 | Emily Dickinson | `dickinson/` | Compressed, elliptical, startling | ✅ Active |
| 8 | Pablo Neruda | `neruda/` | Sensuous, elemental, overflowing | ✅ Active |
| 9 | Rainer Maria Rilke | `rilke/` | Inward, solitary, reverent | ✅ Active |
| 10 | William Blake | `blake/` | Visionary, prophetic, mythic | ✅ Active |
| 11 | Federico García Lorca | `lorca/` | Duende-filled, tragic, Andalusian | ✅ Active |
| 12 | W. B. Yeats | `yeats/` | Mythic, musical, time-haunted | ✅ Active |
| 13 | T. S. Eliot | `eliot/` | Fragmented, allusive, modern | ✅ Active |
| 14 | Hafez | `hafez/` | Intoxicated, playful, wise | ✅ Active |
| 15 | Kazi Nazrul Islam | `nazrul/` | Fiery, rebellious, ecstatic | ✅ Active |
| 16 | Rabindranath Tagore | `rabindranath/` | Songlike, devotional, wonder-filled | ✅ Active |
| 17 | Sukanta Bhattacharya | `sukanta/` | Urgent, revolutionary, hungry for justice | ✅ Active |
| 18 | Shakti Chattopadhyay | `shakti/` | Bohemian, wandering, tenderly ironic | ✅ Active |

---

## Signature Details

### 1. `gibran/` — Kahlil Gibran
The prophetic voice of *The Prophet* (1923): biblical cadence, the seeker's question, the oration, the benediction. Nature as scripture.

### 2. `aurilus/` — Marcus Aurelius
The Stoic prophetic prose: the inner citadel, the fading name, the beloved necessity. Calm force over ornament.

### 3. `jibanananda/` — Jibanananda Das
Twilight-toned lyric: dusk, fields, rivers, memory, and a quiet haunting. Landscape carries feeling.

### 4. `rabindrasangeet/` — Rabindranath Tagore (Sangeet)
Devotional lyric: refrain, verse, reprise. Longing and union before the beloved and the unseen order.

### 5. `rumi/` — Rumi
The ecstatic Sufi: the reed-flute's cry, the wine, the Beloved. Longing turned into union, the wound into light.

### 6. `whitman/` — Walt Whitman
The expansive democrat: the open road, the body electric, the self that contains multitudes.

### 7. `dickinson/` — Emily Dickinson
The compressed recluse: the dash, the slant of light, the infinite packed into a small exact thing.

### 8. `neruda/` — Pablo Neruda
The sensuous elementalist: the onion, the salt, the bread, the body of the beloved and the world.

### 9. `rilke/` — Rainer Maria Rilke
The solitary reverent: the angel, the rose, the inner room, the change you must make.

### 10. `blake/` — William Blake
The visionary prophet: the lamb and the tiger, the grain of sand, the marriage of heaven and hell.

### 11. `lorca/` — Federico García Lorca
The duende poet: the moon, the guitar, the blood, the dark sound of the earth.

### 12. `yeats/` — W. B. Yeats
The mythic musician: the swan, the gyre, the tower, the center that cannot hold.

### 13. `eliot/` — T. S. Eliot
The modern fragmentist: the wasteland, the mermaids, the fragments shored against ruins.

### 14. `hafez/` — Hafez
The intoxicated sage: the wine, the tavern, the beloved, the hidden truth beneath the jest.

### 15. `nazrul/` — Kazi Nazrul Islam
The Rebel Poet: the sword, the flame, the broken shackle, the dawn of equality.

### 16. `rabindranath/` — Rabindranath Tagore
The wonder-filled devotional: the river, the flower, the music of the universe, the far shore.

### 17. `sukanta/` — Sukanta Bhattacharya
The revolutionary: the famine, the hungry child, the coming dawn, the poem as a weapon.

### 18. `shakti/` — Shakti Chattopadhyay
The bohemian wanderer: the road, the forest, the tavern, the lightness that carries the heavy.

---

## How to Add a New Signature

1. Create a folder `poetry/signatures/<name>/`.
2. Write the signature to `poetry/signatures/<name>/signature.md`, following the structure: **Core Movement**, **Motifs**, **Diction**, **Pattern**, **Sample**.
3. Add a row to the table above and a detail section below.
