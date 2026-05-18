# GemmaAudit Video Production Blueprint & Script Copy

This production script is designed to align your **NotebookLM Audio Overview Podcast** (AI Co-hosts discussing your project) with the high-fidelity visual WebP animations and screenshots generated during development. 

Use this table as your timeline guide in **iMovie**, **CapCut**, or any online video compiler.

---

## 📽️ Video Production Script Timeline

| Timecode | On-Screen Visual (Video Track) | Audio Dialogue Theme (NotebookLM Track) |
| :--- | :--- | :--- |
| **0:00 - 0:15** | **The Hook**: Start with a high-contrast crop of the messy legacy COBOL code ([ACC-UPDATE.cbl](file:///Users/yakarteek/code/personal/gemma4_contest/backend/samples/ACC-UPDATE.cbl)). Instantly fade into the sleek, glowing purple and cyan headers of the **GemmaAudit** Dashboard. | **Host A**: "Okay, have you ever looked at 40-year-old mainframe code? It's... a nightmare. Spaghetti variables, massive data layers, zero modularity."<br>**Host B**: "Yeah, it’s a time capsule. But normally, engineers can’t just send this data to a public cloud API due to strict compliance." |
| **0:15 - 0:45** | **Dashboard Overview**: Play a looping clip of `gemma_audit_demo.webp`. Show the user selecting a program, triggering the live side-by-side modernization blueprint (translating COBOL to Python). Highlight the active **Deep Thinking Mode** slider toggle. | **Host A**: "Exactly! Regulated banks and healthcare systems can't leak code. But here is the crazy part: this project, *GemmaAudit*, runs **completely offline**."<br>**Host B**: "Wait, offline? How?"<br>**Host A**: "On a standard consumer GPU! Using Gemma 4 tuned locally with Unsloth. It’s fully air-gapped." |
| **0:45 - 1:25** | **Clustered AST Topology**: Switch to a close-up of `clustered_topology_demo.webp` showing D3 force-directed nodes floating. Highlight the **restructured Legend HUD** on the left. Zoom in on how the nodes physically cluster: Logic programs on the left (purple), Variables on the right (yellow), and sequential storage files at the bottom (cyan). | **Host B**: "Wow, check out that graph! It literally clusters code based on what it does functionally."<br>**Host A**: "Yes! It separates Logic Control flows from memory registers and database boundaries. And notice the lines—solid pathways represent control performing, while dashed paths represent physical database queries. It visually untangles the mess." |
| **1:25 - 2:05** | **Solving the Scale Problem (Graph-RAG)**: Display a clean, split-screen code view. On the left, show [backend/parser.py](file:///Users/yakarteek/code/personal/gemma4_contest/backend/parser.py). On the right, show a Pydantic tool call structure from [backend/main.py](file:///Users/yakarteek/code/personal/gemma4_contest/backend/main.py). Overlay a graphical graphic mapping: `AST Parser -> Context Pruned Graph-RAG Query -> Gemma 4 128K Context Window`. | **Host B**: "But wait, mainframes are huge. How does a local model parse a gigabyte of legacy systems?"<br>**Host A**: "That’s their core technical differentiator. They built a local static AST parser. Instead of blindly sending thousands of files, they run a **Graph-RAG sub-graph query** that feeds Gemma 4 only the immediate dependencies, perfectly fitting its native context window!" |
| **2:05 - 2:45** | **Auditable AI & Collapsible Thinking**: Play a clip showing the XML reasoning terminal trace in the bottom left of the chat window. Zoom in on the collapsible `<thinking>` box expanding to reveal the deep architectural trace, then collapsing as the clean modern Python code is rendered. | **Host B**: "That is brilliant. And I love the explainability here. Mainframe teams need to audit every line."<br>**Host A**: "Absolutely. The model outputs a complete collapsible reasoning trace before generating code, so human auditors can double-check the database mapping and variables life-cycle live." |
| **2:45 - END** | **Call to Action**: Show a beautiful wide shot of the entire dashboard (`dashboard_screenshot.png`). Animate a sleek repository overlay displaying: `github.com/yakarteek/gemmaaudit` and the DEV.to submission headers. | **Host B**: "This isn’t just a simple wrapper; it’s a complete production blueprint for local legacy modernization."<br>**Host A**: "It really is. Air-gapped, parser-grounded, and visually clustered. You can find the entire codebase open-source on GitHub!" |

---

## 🛠️ Video Compilation Steps

1. **Step 1: Download Audio**: Generate and download your NotebookLM **Audio Overview** using [submissions/write_track.md](file:///Users/yakarteek/code/personal/gemma4_contest/submissions/write_track.md).
2. **Step 2: Launch Video Editor**: Drag the audio track into iMovie, CapCut, or Premiere.
3. **Step 3: Overlay Clips**:
   * For **0:00-0:15**, import `dashboard_screenshot.png` and crop the COBOL source file view.
   * For **0:15-0:45**, overlay [gemma_audit_demo.webp](file:///Users/yakarteek/code/personal/gemma4_contest/submissions/assets/gemma_audit_demo.webp) and loop it once.
   * For **0:45-1:25**, overlay [clustered_topology_demo.webp](file:///Users/yakarteek/code/personal/gemma4_contest/submissions/assets/clustered_topology_demo.webp) and loop it once.
   * For **1:25-2:05**, take a screenshot of [backend/parser.py](file:///Users/yakarteek/code/personal/gemma4_contest/backend/parser.py) or record yourself scrolling the code, then place it in the editor.
   * For **2:05-2:45**, crop the bottom-left chat window showing the collapsible thinking logs from `gemma_audit_demo.webp`.
   * For **2:45-END**, display the full `dashboard_screenshot.png` with a text overlay of your GitHub link.
4. **Step 4: Export**: Export the video as a **1080p MP4 file** and publish it directly to YouTube!
