// Global state management
let activeGraphScope = "system"; // "system" or program name
let systemGraphData = null;
let currentGraphData = null;
let currentProgramName = null;
let zoomBehavior = null;
let svgElement = null;
let svgGroup = null;
let forceSimulation = null;

// Color Palette Maps
const colors = {
    program: "#a855f7",
    paragraph: "#ec4899",
    variable: "#eab308",
    file: "#06b6d4",
    table: "#3b82f6",
    job: "#f97316",       // JCL Job — orange, top-of-stack orchestrator
    step: "#fb923c",      // JCL Step — lighter orange, sub-step
    dataset: "#22d3ee"    // Physical DSN — cyan-teal, distinguished from .DAT files
};

// Initialize Dashboard
document.addEventListener("DOMContentLoaded", () => {
    initApp();
    setupEventListeners();
});

async function initApp() {
    // 1. Fetch system graph overview
    await loadSystemGraph();
    
    // 2. Initial welcome layout setup
    document.getElementById("legacy-file-name").textContent = "No module selected";
}

function setupEventListeners() {
    // Switch tabs in Modernization Hub
    document.querySelectorAll(".hub-tab").forEach(tab => {
        tab.addEventListener("click", (e) => {
            document.querySelectorAll(".hub-tab").forEach(t => t.classList.remove("active"));
            document.querySelectorAll(".tab-content").forEach(c => c.classList.remove("active"));
            
            e.target.classList.add("active");
            const targetId = e.target.getAttribute("data-tab");
            document.getElementById(targetId).classList.add("active");
        });
    });

    // Reset back to System Overview button
    document.getElementById("reset-graph-btn").addEventListener("click", () => {
        resetToSystemOverview();
    });

    // Chat form submit
    document.getElementById("chat-form").addEventListener("submit", (e) => {
        e.preventDefault();
        handleChatSubmit();
    });

    // Zoom controls HUD
    document.getElementById("zoom-in-btn").addEventListener("click", () => {
        if (svgElement && zoomBehavior) {
            d3.select(svgElement).transition().duration(300).call(zoomBehavior.scaleBy, 1.3);
        }
    });

    document.getElementById("zoom-out-btn").addEventListener("click", () => {
        if (svgElement && zoomBehavior) {
            d3.select(svgElement).transition().duration(300).call(zoomBehavior.scaleBy, 0.7);
        }
    });

    document.getElementById("fit-screen-btn").addEventListener("click", () => {
        fitGraphToViewport();
    });
}

// Fetch and load System Graph Overview
async function loadSystemGraph() {
    const listContainer = document.getElementById("module-list");
    listContainer.innerHTML = `<div class="loading-placeholder"><i class="fa-solid fa-spinner fa-spin"></i> Fetching system overview...</div>`;
    
    try {
        const response = await fetch("/api/graph");
        if (!response.ok) throw new Error("Graph API response failure");
        
        systemGraphData = await response.json();
        currentGraphData = systemGraphData;
        activeGraphScope = "system";
        
        document.getElementById("active-graph-scope").textContent = "System Overview";
        document.getElementById("reset-graph-btn").style.display = "none";
        
        // Render D3 Graph topology
        renderD3Graph(systemGraphData);
        
        // Populate the Legacy inventory side list
        populateInventory(systemGraphData);
        
    } catch (error) {
        console.error("Error loading system graph:", error);
        listContainer.innerHTML = `<div class="loading-placeholder text-danger"><i class="fa-solid fa-triangle-exclamation"></i> Error loading inventory.</div>`;
    }
}

// Fetch and load detailed program graph
async function loadProgramGraph(programName) {
    activeGraphScope = programName;
    currentProgramName = programName;
    document.getElementById("active-graph-scope").textContent = `${programName} AST`;
    document.getElementById("reset-graph-btn").style.display = "inline-flex";
    
    // Highlight correct item in explorer sidebar list
    document.querySelectorAll(".explorer-item").forEach(item => {
        const title = item.querySelector(".item-title").textContent;
        if (title === programName || title.replace(".CBL", "").replace(".COB", "") === programName.replace(".CBL", "").replace(".COB", "")) {
            item.classList.add("active");
        } else {
            item.classList.remove("active");
        }
    });
    
    try {
        // Fetch detailed graph nodes
        const graphResponse = await fetch(`/api/graph?program=${encodeURIComponent(programName)}`);
        if (!graphResponse.ok) throw new Error("Program Graph API failure");
        const graphData = await graphResponse.json();
        currentGraphData = graphData;
        renderD3Graph(graphData);
        
        // Fetch source code
        loadProgramSource(programName);
        
    } catch (error) {
        console.error("Error loading program graph:", error);
    }
}

// Fetch program source code and load into Code Viewer tabs
async function loadProgramSource(programName) {
    const legacyBox = document.getElementById("legacy-code-box");
    const blueprintBox = document.getElementById("blueprint-code-box");
    const legacyNameLabel = document.getElementById("legacy-file-name");
    const locLabel = document.getElementById("legacy-loc");
    
    legacyBox.textContent = "* Loading source code from audit scope...";
    blueprintBox.textContent = "# Analyzing legacy structure and compiling microservice blueprint...";
    
    try {
        const response = await fetch(`/api/source?program=${encodeURIComponent(programName)}`);
        if (!response.ok) throw new Error("Source Code API failure");
        const data = await response.json();
        
        legacyNameLabel.textContent = `${programName.toUpperCase()}`;
        const loc = data.content.split("\n").length;
        locLabel.textContent = `${loc} LOC`;
        
        legacyBox.textContent = data.content;
        
        // Switch to "Legacy Code" tab initially
        document.getElementById("tab-legacy").click();
        
        // Trigger automated blueprint translation layout locally for visual preview
        generateMockBlueprint(programName, data.content);
        
    } catch (error) {
        console.error("Error loading program source:", error);
        legacyNameLabel.textContent = "Source Load Failed";
        legacyBox.textContent = `* ERROR: Source code for '${programName}' could not be loaded.\n* Check file availability in the COBOL directories.`;
    }
}

// Locally compile mock blueprint translations based on clicked program to keep UI interactive
function generateMockBlueprint(programName, sourceCode) {
    const blueprintBox = document.getElementById("blueprint-code-box");
    const cleanName = programName.toUpperCase().replace(".CBL", "").replace(".COB", "");
    
    let pythonCode = "";
    if (cleanName.includes("MORTGAGE")) {
        pythonCode = `from pydantic import BaseModel, Field
from fastapi import FastAPI, HTTPException

app = FastAPI(title="Mortgage Calculator microservice")

class AmortizationRequest(BaseModel):
    balance: float = Field(..., description="Outstanding principal balance", gt=0)
    interest_rate: float = Field(..., description="Annual interest rate in %", gt=0, le=25)
    term_months: int = Field(360, description="Amortization term in months")

@app.post("/calculate-amortization")
def apply_amortization_formula(req: AmortizationRequest):
    """
    Stateless translation of paragraph 4000-APPLY-AMORTIZATION-FORMULA.
    Calculates monthly compounding payments using isolated local variables.
    """
    monthly_rate = req.interest_rate / 1200.0
    factor = (1.0 + monthly_rate) ** req.term_months
    
    try:
        monthly_payment = req.balance * (monthly_rate * factor) / (factor - 1.0)
        return {
            "status": "success",
            "monthly_payment": round(monthly_payment, 2),
            "total_payout": round(monthly_payment * req.term_months, 2),
            "interest_portion": round((monthly_payment * req.term_months) - req.balance, 2)
        }
    except ZeroDivisionError:
        raise HTTPException(status_code=400, detail="Invalid interest calculation limits.")
`;
    } else if (cleanName.includes("DB-INTERFACE")) {
        pythonCode = `import os
from typing import Optional
from pydantic import BaseModel
from sqlalchemy import create_engine, Column, Integer, String, Float
from sqlalchemy.orm import declarative_base, sessionmaker

# Configured for modern cloud SQL stores rather than mainframe DB2 ECI connections
DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://db_interface_user:secure@localhost:5432/corp_db")
engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

class DB2AccountRecord(Base):
    __tablename__ = "accounts"
    account_number = Column(String(10), primary_key=True, index=True)
    customer_name = Column(String(50), nullable=False)
    balance = Column(Float, default=0.0)

class AccountUpdate(BaseModel):
    account_number: str
    balance: float

def execute_account_query(acc_num: str) -> Optional[DB2AccountRecord]:
    """
    Replaces EXEC SQL SELECT ... FROM DB2_ACCOUNT_TABLE INTO :LK-RECORD-VARS.
    """
    db = SessionLocal()
    try:
        return db.query(DB2AccountRecord).filter(DB2AccountRecord.account_number == acc_num).first()
    finally:
        db.close()
`;
    } else {
        pythonCode = `import httpx
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

app = FastAPI(title="Legacy ${cleanName} Modernized Orchestrator")

class ModernOrchestratorPayload(BaseModel):
    client_id: str
    amount: float
    rate_multiplier: float

@app.post("/orchestrate")
async def handle_process_flow(payload: ModernOrchestratorPayload):
    """
    Translates program perform-loops of ${cleanName}.cbl.
    Replaces direct assembly CALL statements with secure HTTP microservice bindings.
    """
    fee = 15.00
    net_amount = payload.amount - fee if payload.amount <= 50000.0 else payload.amount - (fee * 0.5)
    
    # ECI CALL wrapper replaces direct memory couplings
    async with httpx.AsyncClient() as client:
        try:
            res = await client.post("http://mortgage-service/calculate-amortization", json={
                "balance": net_amount,
                "interest_rate": payload.rate_multiplier,
                "term_months": 360
            })
            calc_data = res.json()
            return {
                "clientId": payload.client_id,
                "clearedAmount": net_amount,
                "paymentPlan": calc_data
            }
        except httpx.RequestError:
            raise HTTPException(status_code=502, detail="Dependent microservice calculator unavailable.")
`;
    }
    
    blueprintBox.textContent = pythonCode;
}

// Reset view back to macro system overview
function resetToSystemOverview() {
    loadSystemGraph();
    document.getElementById("legacy-file-name").textContent = "No module selected";
    document.getElementById("legacy-loc").textContent = "0 LOC";
    document.getElementById("legacy-code-box").textContent = "* SELECT A LEGACY MODULE FROM THE EXPLORER\n* OR CLICK A GRAPH NODE TO AUDIT SOURCE CODE LIVE.";
    document.getElementById("blueprint-code-box").textContent = "# SELECT A LEGACY MODULE OR PARAGRAPH\n# TO GENERATE STATELESS PYTHON MICROSERVICES equivalent.";
}

// Populates Legacy explorer sidebar items list
function populateInventory(graph) {
    const listContainer = document.getElementById("module-list");
    listContainer.innerHTML = "";
    
    // Extract only Program nodes
    const programs = graph.nodes.filter(n => n.type === "program");
    document.getElementById("module-count").textContent = `${programs.length} Modules`;
    
    if (programs.length === 0) {
        listContainer.innerHTML = `<div class="loading-placeholder">No programs detected.</div>`;
        return;
    }
    
    // Sort program nodes by risk descending
    programs.sort((a, b) => {
        const rA = a.details ? a.details.riskIndex || 0 : 0;
        const rB = b.details ? b.details.riskIndex || 0 : 0;
        return rB - rA;
    });
    
    programs.forEach(prog => {
        const rIndex = prog.details ? prog.details.riskIndex || 10 : 10;
        const loc = prog.details ? prog.details.loc || 0 : 0;
        const hasSql = prog.details ? prog.details.hasSql : false;
        
        let badgeClass = "badge-low";
        let badgeText = "Low Risk";
        if (rIndex > 50) {
            badgeClass = "badge-high";
            badgeText = "HIGH RISK";
        } else if (rIndex >= 30) {
            badgeClass = "badge-mid";
            badgeText = "Mid Risk";
        }
        
        const item = document.createElement("div");
        item.className = "explorer-item";
        item.innerHTML = `
            <div class="explorer-item-name">
                <span class="item-title">${prog.label}</span>
                <span class="item-meta">
                    <i class="fa-solid fa-lines-leaning"></i> ${loc} LOC 
                    ${hasSql ? ' | <i class="fa-solid fa-database" title="DB2 SQL bindings" style="color: var(--neon-cyan);"></i> DB2' : ''}
                </span>
            </div>
            <span class="explorer-item-badge ${badgeClass}">${badgeText} (${rIndex})</span>
        `;
        
        item.addEventListener("click", () => {
            loadProgramGraph(prog.id);
        });
        
        listContainer.appendChild(item);
    });
}

// Re-renders graph SVG using D3 force simulation
function renderD3Graph(graphData) {
    const container = document.getElementById("d3-graph-canvas");
    container.innerHTML = ""; // Clear canvas
    
    const width = container.clientWidth;
    const height = container.clientHeight || 500;
    
    const svg = d3.select("#d3-graph-canvas")
        .append("svg")
        .attr("width", "100%")
        .attr("height", "100%")
        .attr("viewBox", `0 0 ${width} ${height}`)
        .attr("preserveAspectRatio", "xMidYMid meet");
        
    svgElement = svg.node();
    
    // Zoom/Pan setup
    zoomBehavior = d3.zoom()
        .scaleExtent([0.15, 3.5])
        .on("zoom", (event) => {
            svgGroup.attr("transform", event.transform);
        });
        
    svg.call(zoomBehavior);
    
    // Group container for zoom transform
    svgGroup = svg.append("g");
    
    // SVG Lineage marker arrow descriptors
    svg.append("defs").selectAll("marker")
        .data(["calls", "accesses", "queries", "contains", "performs", "rel"])
        .enter().append("marker")
        .attr("id", d => `arrow-${d}`)
        .attr("viewBox", "0 -5 10 10")
        .attr("refX", 22) // distance from node center
        .attr("refY", 0)
        .attr("markerWidth", 5)
        .attr("markerHeight", 5)
        .attr("orient", "auto")
        .append("path")
        .attr("fill", d => {
            if (d === "calls") return colors.program;
            if (d === "contains" || d === "performs") return colors.paragraph;
            if (d === "accesses") return colors.file;
            if (d === "queries") return colors.table;
            return "#64748b";
        })
        .attr("d", "M0,-5L10,0L0,5");
        
    // 1. Draw Links
    const link = svgGroup.append("g")
        .attr("class", "links")
        .selectAll("line")
        .data(graphData.edges)
        .enter().append("line")
        .attr("class", "graph-link")
        .attr("stroke", d => {
            const t = d.type.toLowerCase();
            if (t === "calls") return colors.program;
            if (t === "contains" || t === "performs") return colors.paragraph;
            if (t === "accesses") return colors.file;
            if (t === "queries") return colors.table;
            return "#475569";
        })
        .attr("stroke-width", d => {
            const t = d.type.toLowerCase();
            if (t === "calls" || t === "performs") return 2; // Logic Control is thick
            return 1.2;
        })
        .attr("stroke-dasharray", d => {
            const t = d.type.toLowerCase();
            if (t === "accesses" || t === "queries") return "4,4"; // Storage boundaries are dashed
            return "none";
        })
        .attr("marker-end", d => `url(#arrow-${d.type.toLowerCase()})`);
        
    // 2. Draw Nodes Groups
    const node = svgGroup.append("g")
        .attr("class", "nodes")
        .selectAll("g")
        .data(graphData.nodes)
        .enter().append("g")
        .attr("class", "graph-node")
        .call(d3.drag()
            .on("start", dragstarted)
            .on("drag", dragged)
            .on("end", dragended))
        .on("click", (event, d) => {
            event.stopPropagation();
            handleNodeClick(d);
        });
        
    // Add pulsing outer indicator ring for high-risk program nodes
    node.filter(d => d.type === "program" && d.details && d.details.riskIndex > 50)
        .append("circle")
        .attr("r", 15)
        .attr("fill", "none")
        .attr("stroke", varName => colors.program)
        .attr("class", "pulsing-ring");
 
    // Add main node body circle
    node.append("circle")
        .attr("r", d => {
            if (d.type === "job") return 13;
            if (d.type === "step") return 9;
            if (d.type === "program") return 11;
            if (d.type === "file" || d.type === "table" || d.type === "dataset") return 9;
            return 7;
        })
        .attr("fill", d => colors[d.type] || "#64748b")
        .attr("filter", d => `drop-shadow(0 0 6px ${colors[d.type] || '#64748b'}80)`);
        
    // Add text labels
    node.append("text")
        .attr("class", "node-label")
        .attr("dx", 14)
        .attr("dy", 4)
        .text(d => d.label);
        
    // Add brief info titles on hover
    node.append("title")
        .text(d => {
            const risk = d.details && d.details.riskIndex ? `\nMigration Risk Index: ${d.details.riskIndex}/100` : "";
            const loc = d.details && d.details.loc ? `\nLines of Code: ${d.details.loc}` : "";
            return `Name: ${d.label}\nType: ${d.type.toUpperCase()}${loc}${risk}`;
        });
        
    // Define functional cluster center coordinates
    const getClusterX = d => {
        if (d.type === "job" || d.type === "step") return width * 0.5;            // Orchestration: top-center
        if (d.type === "program" || d.type === "paragraph") return width * 0.33;   // Logic: Left Area
        if (d.type === "variable") return width * 0.67;                            // Memory State: Right Area
        return width * 0.5;                                                        // Storage I/O: Bottom-Center
    };

    const getClusterY = d => {
        if (d.type === "job" || d.type === "step") return height * 0.15;           // Orchestration: top tier
        if (d.type === "program" || d.type === "paragraph") return height * 0.45;
        if (d.type === "variable") return height * 0.45;
        return height * 0.78;                                                      // Storage / Datasets: bottom
    };

    // 3. Setup Simulation Forces
    forceSimulation = d3.forceSimulation(graphData.nodes)
        .force("link", d3.forceLink(graphData.edges).id(d => d.id).distance(d => {
            if (activeGraphScope === "system") return 120;
            return 60;
        }))
        .force("charge", d3.forceManyBody().strength(d => {
            if (activeGraphScope === "system") return -180;
            return -80;
        }))
        .force("collide", d3.forceCollide().radius(25))
        .force("x", d3.forceX().x(getClusterX).strength(activeGraphScope === "system" ? 0.06 : 0.12))
        .force("y", d3.forceY().y(getClusterY).strength(activeGraphScope === "system" ? 0.06 : 0.12))
        .force("center", d3.forceCenter(width / 2, height / 2));
        
    forceSimulation.on("tick", () => {
        link
            .attr("x1", d => d.source.x)
            .attr("y1", d => d.source.y)
            .attr("x2", d => d.target.x)
            .attr("y2", d => d.target.y);
 
        node
            .attr("transform", d => `translate(${d.x},${d.y})`);
    });
    
    // Fit graph inside viewport on load
    setTimeout(fitGraphToViewport, 200);
}

// Drag actions callbacks
function dragstarted(event, d) {
    if (!event.active) forceSimulation.alphaTarget(0.3).restart();
    d.fx = d.x;
    d.fy = d.y;
}

function dragged(event, d) {
    d.fx = event.x;
    d.fy = event.y;
}

function dragended(event, d) {
    if (!event.active) forceSimulation.alphaTarget(0);
    d.fx = null;
    d.fy = null;
}

// Handle clicking a node inside SVG visualizer
function handleNodeClick(nodeData) {
    console.log("Node clicked:", nodeData);
    
    if (activeGraphScope === "system") {
        if (nodeData.type === "program") {
            // Load program AST details
            loadProgramGraph(nodeData.id);
        } else if (nodeData.type === "file") {
            // Put file details into agent console context
            askAgentAboutNode(nodeData.label, "file");
        }
    } else {
        // Detailed program scope clicks
        if (nodeData.type === "paragraph") {
            // Pull code paragraph view on code viewer tab
            highlightCodeParagraph(nodeData.label);
        } else {
            askAgentAboutNode(nodeData.label, nodeData.type);
        }
    }
}

// Prompt agent directly when clicking file/variable nodes
function askAgentAboutNode(name, type) {
    const chatInput = document.getElementById("chat-input");
    chatInput.value = `Explain the usage and structure of ${type} '${name}' in this codebase.`;
    document.getElementById("chat-submit-btn").click();
}

// Search and highlight selected paragraph lines inside Legacy code pre editor
function highlightCodeParagraph(paragraphName) {
    const legacyBox = document.getElementById("legacy-code-box");
    const rawCode = legacyBox.textContent;
    const lines = rawCode.split("\n");
    
    let startIdx = -1;
    let endIdx = -1;
    
    for (let i = 0; i < lines.length; i++) {
        // Match paragraph declarations: e.g. "1000-PROCESS-DATA."
        if (lines[i].includes(paragraphName) && lines[i].trim().endsWith(".")) {
            startIdx = i;
            // Find end: next paragraph or end of division (starts in area A or matches another paragraph pattern)
            for (let j = i + 1; j < lines.length; j++) {
                if (lines[j].trim().endsWith(".") && /^\s{0,4}[A-Za-z0-9\-]+\s*\.\s*$/.test(lines[j])) {
                    endIdx = j;
                    break;
                }
            }
            if (endIdx === -1) endIdx = lines.length;
            break;
        }
    }
    
    if (startIdx !== -1) {
        // Switch to legacy tab
        document.getElementById("tab-legacy").click();
        
        // Scroll the pre box to center the paragraph
        const linesHeight = 20; // estimate line height in pixels
        const container = document.querySelector(".code-editor-box");
        container.scrollTop = startIdx * linesHeight - 60;
        
        // Temporarily change font weights to highlight the paragraph lines
        // For simplicity in vanilla JS, we replace content with a colored section
        const highlightedLines = lines.map((l, index) => {
            if (index >= startIdx && index < endIdx) {
                return `>> [HL] ${l}`;
            }
            return l;
        }).join("\n");
        
        legacyBox.textContent = highlightedLines;
        
        // Reset code back to normal after 5 seconds
        setTimeout(() => {
            legacyBox.textContent = rawCode;
        }, 5000);
    }
}

// Zoom D3 graph bounding box to fully fit SVG container dimensions
function fitGraphToViewport() {
    if (!svgElement || !svgGroup || !currentGraphData || currentGraphData.nodes.length === 0) return;
    
    const container = document.getElementById("d3-graph-canvas");
    const width = container.clientWidth;
    const height = container.clientHeight || 500;
    
    // Collect coordinates bounding box
    let minX = Infinity, maxX = -Infinity, minY = Infinity, maxY = -Infinity;
    currentGraphData.nodes.forEach(n => {
        if (n.x < minX) minX = n.x;
        if (n.x > maxX) maxX = n.x;
        if (n.y < minY) minY = n.y;
        if (n.y > maxY) maxY = n.y;
    });
    
    // Fallback if coordinates aren't ticked/initialized yet
    if (minX === Infinity) return;
    
    const dx = maxX - minX || 100;
    const dy = maxY - minY || 100;
    const cx = (minX + maxX) / 2;
    const cy = (minY + maxY) / 2;
    
    const scale = Math.max(0.2, Math.min(2.0, 0.85 / Math.max(dx / width, dy / height)));
    const translate = [width / 2 - scale * cx, height / 2 - scale * cy];
    
    d3.select(svgElement).transition().duration(500).call(
        zoomBehavior.transform,
        d3.zoomIdentity.translate(translate[0], translate[1]).scale(scale)
    );
}

// Chat submit processing
async function handleChatSubmit() {
    const chatInput = document.getElementById("chat-input");
    const message = chatInput.value.trim();
    if (!message) return;
    
    // Clear input
    chatInput.value = "";
    
    // Append User Message bubble
    appendChatMessage(message, "user");
    
    // Append Loading reasoning placeholder bubble
    const loadingBubbleId = appendLoadingBubble();
    
    const selectedModel = document.getElementById("model-selector").value;
    const thinkingMode = document.getElementById("thinking-mode-toggle").checked;
    
    try {
        const response = await fetch("/api/chat", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({
                message: message,
                model: selectedModel,
                thinkingMode: thinkingMode
            })
        });
        
        if (!response.ok) throw new Error("Agent failed to respond.");
        const data = await response.json();
        
        // Remove loading state bubble
        removeBubble(loadingBubbleId);
        
        // Parse and append bot message bubble
        appendAgentResponse(data.response);
        
    } catch (error) {
        removeBubble(loadingBubbleId);
        appendChatMessage("⚠️ Failed to communicate with offline Gemma 4 agent server. Please confirm the FastAPI dev server is running on port 8000.", "bot");
    }
}

// Appends normal text messages
function appendChatMessage(text, sender) {
    const thread = document.getElementById("chat-thread");
    const bubble = document.createElement("div");
    bubble.className = `chat-bubble ${sender}-message`;
    
    const senderIcon = sender === "user" ? "fa-user-pen" : "fa-microchip-heading";
    const senderName = sender === "user" ? "User Auditor" : "GemmaAudit Agent";
    
    bubble.innerHTML = `
        <div class="message-sender">
            <i class="fa-solid ${senderIcon}"></i>
            <span>${senderName}</span>
        </div>
        <div class="message-content">
            <p>${formatMarkdown(text)}</p>
        </div>
    `;
    
    thread.appendChild(bubble);
    thread.scrollTop = thread.scrollHeight;
}

// Appends load indicator spinner
function appendLoadingBubble() {
    const thread = document.getElementById("chat-thread");
    const id = "loading-" + Date.now();
    const bubble = document.createElement("div");
    bubble.className = `chat-bubble bot-message`;
    bubble.id = id;
    
    bubble.innerHTML = `
        <div class="message-sender">
            <i class="fa-solid fa-microchip-heading"></i>
            <span>GemmaAudit Agent</span>
        </div>
        <div class="message-content">
            <p><i class="fa-solid fa-circle-nodes fa-spin" style="color: var(--neon-cyan);"></i> Analyzing graph topology and reasoning offline...</p>
        </div>
    `;
    
    thread.appendChild(bubble);
    thread.scrollTop = thread.scrollHeight;
    return id;
}

function removeBubble(id) {
    const elem = document.getElementById(id);
    if (elem) elem.remove();
}

// Separates XML thinking and normal responses and formats them beautifully
function appendAgentResponse(fullResponseText) {
    const thread = document.getElementById("chat-thread");
    const bubble = document.createElement("div");
    bubble.className = `chat-bubble bot-message`;
    
    let thinkingHtml = "";
    let cleanResponseText = fullResponseText;
    
    // Extract <thinking>...</thinking> blocks
    const thinkingMatch = fullResponseText.match(/<thinking>([\s\S]*?)<\/thinking>/);
    if (thinkingMatch) {
        const thinkingTrace = thinkingMatch[1].trim();
        const randId = "trace-" + Math.floor(Math.random() * 10000);
        
        thinkingHtml = `
            <div class="thinking-block-container">
                <div class="thinking-header" onclick="toggleThinking('${randId}')" id="hdr-${randId}">
                    <span><i class="fa-solid fa-terminal"></i> Gemma 4 Offline Reasoning Trace</span>
                    <i class="fa-solid fa-chevron-down"></i>
                </div>
                <div class="thinking-content" id="cnt-${randId}">
${escapeHtml(thinkingTrace)}
                </div>
            </div>
        `;
        
        // Remove thinking block from final display
        cleanResponseText = fullResponseText.replace(/<thinking>[\s\S]*?<\/thinking>/, "").trim();
    }
    
    bubble.innerHTML = `
        <div class="message-sender">
            <i class="fa-solid fa-microchip-heading"></i>
            <span>GemmaAudit Agent</span>
        </div>
        <div class="message-content">
            ${thinkingHtml}
            <div>${formatMarkdown(cleanResponseText)}</div>
        </div>
    `;
    
    thread.appendChild(bubble);
    thread.scrollTop = thread.scrollHeight;
}

// Collapsible thinking console click handler
window.toggleThinking = function(id) {
    const header = document.getElementById(`hdr-${id}`);
    const content = document.getElementById(`cnt-${id}`);
    
    if (header && content) {
        header.classList.toggle("collapsed");
        content.classList.toggle("collapsed");
    }
};

// Extremely basic inline markdown converter for rich text
function formatMarkdown(text) {
    // Escape HTML first to prevent injection in code blocks
    let formatted = text;
    
    // Render bold
    formatted = formatted.replace(/\*\*(.*?)\*\*/g, "<strong>$1</strong>");
    formatted = formatted.replace(/\*(.*?)\*/g, "<em>$1</em>");
    
    // Code blocks `...`
    formatted = formatted.replace(/`(.*?)`/g, "<code class='inline-code'>$1</code>");
    
    // Bullet lists
    formatted = formatted.replace(/^\s*-\s+(.*?)$/gm, "<li>$1</li>");
    formatted = formatted.replace(/(<li>.*?<\/li>)+/g, "<ul>$&</ul>");
    
    // Double newlines into paragraphs
    formatted = formatted.replace(/\n\n/g, "<br><br>");
    
    return formatted;
}

function escapeHtml(string) {
    const map = {
        '&': '&amp;',
        '<': '&lt;',
        '>': '&gt;',
        '"': '&quot;',
        "'": '&#039;'
    };
    return string.replace(/[&<>"']/g, function(m) { return map[m]; });
}
