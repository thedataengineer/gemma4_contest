# GemmaAudit Video Production Blueprint & Script Copy

This production script is designed to align your **NotebookLM Audio Overview Podcast** (AI Co-hosts discussing your project) with the high-fidelity visual WebP animations and screenshots generated during development. 

Use this table as your timeline guide in **iMovie**, **CapCut**, or any online video compiler.

---

## 📽️ Video Production Script Timeline

| Timecode | On-Screen Visual (Video Track) | Audio Dialogue Theme (NotebookLM Track) |
| :--- | :--- | :--- |
| **0:00 - 0:15** | **The Hook**: Start with a high-contrast crop of the messy legacy COBOL code ([ACC-UPDATE.cbl](file:///Users/yakarteek/code/personal/gemma4_contest/backend/samples/ACC-UPDATE.cbl)), then a flash of the cryptic JCL that schedules it ([NIGHTLY.jcl](file:///Users/yakarteek/code/personal/gemma4_contest/backend/samples/NIGHTLY.jcl)). Instantly fade into the sleek, glowing purple and cyan headers of the **GemmaAudit** Dashboard. | **Host A**: "Okay, have you ever looked at 40-year-old mainframe code? It's... a nightmare. Spaghetti variables, massive data layers, zero modularity — and cryptic JCL batch scripts wrapped around all of it."<br>**Host B**: "Yeah, it’s a time capsule. But normally, engineers can’t just send this data to a public cloud API due to strict compliance." |
| **0:15 - 0:45** | **Dashboard Overview**: Play a looping clip of `gemma_audit_demo.webp`. Show the user selecting a program, triggering the live side-by-side modernization blueprint (translating COBOL to Python). Highlight the active **Deep Thinking Mode** slider toggle. | **Host A**: "Exactly! Regulated banks and healthcare systems can't leak code. But here is the crazy part: this project, *GemmaAudit*, runs **completely offline**."<br>**Host B**: "Wait, offline? How?"<br>**Host A**: "On a standard consumer GPU! Using Gemma 4 tuned locally with Unsloth. It’s fully air-gapped." |
| **0:45 - 1:25** | **Clustered JCL→COBOL Topology**: Switch to a close-up of `clustered_topology_demo.webp` showing D3 force-directed nodes floating. Highlight the **restructured Legend HUD** on the left, leading with the new orange **Orchestration (JCL)** section. Zoom in on the three physical tiers: orange JCL Jobs & Steps clustered at the **top**, purple Logic programs and pink paragraphs in the **middle**, and cyan Datasets / Files / DB2 tables at the **bottom**. Trace one `Step → EXECUTES → Program` edge from a JCL job down into the COBOL it schedules. | **Host B**: "Wow, check out that graph! It clusters everything by what it does — and that orange band at the top, those are the JCL batch jobs?"<br>**Host A**: "Exactly. Most demos skip JCL entirely — it's the master controller that schedules the COBOL. GemmaAudit parses it, so you see the full stack: a JCL Step executes a program, that program PERFORMs its paragraphs, which touch the datasets. It visually untangles the entire orchestration." |
| **1:25 - 2:05** | **Solving the Scale Problem (Graph-RAG + Validation)**: Display a clean, split-screen code view. On the left, show [backend/parser.py](file:///Users/yakarteek/code/personal/gemma4_contest/backend/parser.py) and [backend/jcl_parser.py](file:///Users/yakarteek/code/personal/gemma4_contest/backend/jcl_parser.py). On the right, show the function-calling tool schema from [backend/main.py](file:///Users/yakarteek/code/personal/gemma4_contest/backend/main.py). Overlay a graphic mapping: `ANTLR4 COBOL + JCL Parser -> Unified Knowledge Graph -> Context-Pruned Sub-Graph Query -> Gemma 4 128K Context Window`. Flash a stat card: **"6,191 COBOL files parsed · 99.90% pass rate"**. | **Host B**: "But wait, mainframes are huge. How does a local model handle a gigabyte of legacy systems?"<br>**Host A**: "That’s the core technical differentiator. A custom ANTLR4 COBOL parser — battle-tested on over six thousand real files at a 99.9% pass rate — plus a two-stage JCL parser. Instead of blindly sending thousands of files, it runs a **Graph-RAG sub-graph query** that feeds Gemma 4 only the immediate dependencies, perfectly fitting its native 128K context window." |
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
