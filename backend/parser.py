import os
import re
import json

from backend.jcl_parser import JclParser


class CobolParser:
    def __init__(self, samples_dir=None, custom_kg_dir="/Users/yakarteek/code/personal/cobol-parser/python-parser/data/kg",
                 jcl_llm_enrich=True):
        self.samples_dir = samples_dir
        self.custom_kg_dir = custom_kg_dir
        self.jcl_parser = JclParser(samples_dir, llm_enrich=jcl_llm_enrich)
        self._jcl_cache = None
        self.nodes = {}
        self.edges = []

    def _jcl_graph(self):
        """Lazy cached call to the JCL parser so we don't re-parse on every request."""
        if self._jcl_cache is None:
            self._jcl_cache = self.jcl_parser.parse_directory()
        return self._jcl_cache
        
    def sanitize_line(self, line):
        """Removes COBOL sequence numbers (cols 1-6) and handles comments (col 7 is '*')."""
        if len(line) < 6:
            return ""
        # Remove sequence numbers
        content = line[6:].rstrip()
        if not content:
            return ""
        # Check for comment character in column 7 (first character after sequence number)
        if content[0] in ['*', '/']:
            return ""
        return content

    def calculate_complexity(self, lines):
        """Approximates cyclomatic complexity based on control flow keywords."""
        complexity = 1
        keywords = [
            r'\bIF\b', r'\bEVALUATE\b', r'\bPERFORM\s+UNTIL\b', r'\bPERFORM\s+VARYING\b',
            r'\bAND\b', r'\bOR\b', r'\bWHEN\b', r'\bON\s+SIZE\s+ERROR\b', r'\bINVALID\s+KEY\b'
        ]
        for line in lines:
            line_upper = line.upper()
            for kw in keywords:
                complexity += len(re.findall(kw, line_upper))
        return complexity

    def extract_paragraphs(self, lines):
        """Extracts paragraph names and their lines."""
        paragraphs = {}
        current_para = None
        para_lines = []
        
        # Regex to detect paragraph names: e.g., "1000-PROCESS-DATA."
        # Must start in Area A (first few characters) and end with a period.
        para_pattern = re.compile(r'^\s*([A-Za-z0-9\-]+)\s*\.\s*$')
        
        in_procedure_division = False
        
        for line in lines:
            line_upper = line.upper()
            if "PROCEDURE DIVISION" in line_upper:
                in_procedure_division = True
                continue
                
            if not in_procedure_division:
                continue
                
            match = para_pattern.match(line)
            if match:
                if current_para:
                    paragraphs[current_para] = para_lines
                current_para = match.group(1)
                para_lines = []
            elif current_para:
                para_lines.append(line)
                
        if current_para and para_lines:
            paragraphs[current_para] = para_lines
            
        return paragraphs

    def parse_file(self, file_path):
        """Parses a single COBOL file to extract structural metadata, variables, flow, and database interactions."""
        filename = os.path.basename(file_path)
        program_name = os.path.splitext(filename)[0]
        
        with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
            raw_lines = f.readlines()
            
        lines = [self.sanitize_line(l) for l in raw_lines]
        lines = [l for l in lines if l.strip()] # filter empty lines
        
        # Determine Program Name from PROGRAM-ID
        program_id_match = re.search(r'PROGRAM-ID\.\s+([A-Za-z0-9\-]+)', "\n".join(lines), re.IGNORECASE)
        if program_id_match:
            program_name = program_id_match.group(1)
            
        # Basic Metrics
        loc = len(lines)
        complexity = self.calculate_complexity(lines)
        
        # Extract Paragraphs
        paragraphs = self.extract_paragraphs(lines)
        
        # Calculate Migration Risk Index (MRI)
        # Based on complexity (50%), LOC (30%), and special features like database or nested calls (20%)
        mri = min(100, int((complexity * 1.8) + (loc * 0.05)))
        
        # Check for DB2/SQL usage
        has_sql = any("EXEC SQL" in l.upper() for l in lines)
        if has_sql:
            mri = min(100, mri + 15)
            
        # Check for External CALLs
        external_calls = []
        call_pattern = re.compile(r'\bCALL\s+[\'\"]([A-Za-z0-9\-]+)[\'\"]', re.IGNORECASE)
        for line in lines:
            matches = call_pattern.findall(line)
            for m in matches:
                if m not in external_calls and m != program_name:
                    external_calls.append(m)
                    
        # Check for File I/O
        files_accessed = []
        select_pattern = re.compile(r'\bSELECT\s+([A-Za-z0-9\-]+)\s+ASSIGN\b', re.IGNORECASE)
        for line in lines:
            match = select_pattern.search(line)
            if match:
                files_accessed.append(match.group(1))
                
        # Parse Variable declarations in WORKING-STORAGE
        in_working_storage = False
        variables = []
        var_pattern = re.compile(r'^\s*(01|05|10|15|77|88)\s+([A-Za-z0-9\-]+)(?:\s+PIC\s+([A-Za-z0-9()V]+))?', re.IGNORECASE)
        
        for line in lines:
            line_upper = line.upper()
            if "WORKING-STORAGE SECTION" in line_upper:
                in_working_storage = True
                continue
            if "PROCEDURE DIVISION" in line_upper or "LINKAGE SECTION" in line_upper:
                in_working_storage = False
                
            if in_working_storage:
                match = var_pattern.match(line)
                if match:
                    level = match.group(1)
                    var_name = match.group(2)
                    pic = match.group(3) or "GROUP"
                    if var_name.upper() not in ["FILLER"]:
                        variables.append((var_name, level, pic))
                        
        # Register main program node
        self.nodes[program_name] = {
            "id": program_name,
            "label": f"{program_name}.CBL",
            "type": "program",
            "details": {
                "loc": loc,
                "complexity": complexity,
                "riskIndex": mri,
                "hasSql": has_sql,
                "files": files_accessed,
                "externalCalls": external_calls,
                "description": f"Main program orchestrating business operations inside {program_name}."
            }
        }
        
        # Register Variable Nodes & Edges
        for var_name, level, pic in variables:
            var_node_id = f"{program_name}:{var_name}"
            self.nodes[var_node_id] = {
                "id": var_node_id,
                "label": f"{var_name} ({pic})",
                "type": "variable",
                "details": {
                    "description": f"Variable level {level} declared in WORKING-STORAGE memory block."
                }
            }
            self.edges.append({
                "source": program_name,
                "target": var_node_id,
                "type": "contains",
                "label": "CONTAINS"
            })
        
        # Register Paragraph Nodes & Control Flow Edges
        for para, para_content in paragraphs.items():
            para_id = f"{program_name}:{para}"
            self.nodes[para_id] = {
                "id": para_id,
                "label": para,
                "type": "paragraph",
                "details": {
                    "loc": len(para_content),
                    "complexity": self.calculate_complexity(para_content),
                    "description": f"Logical block inside {program_name} dedicated to functional routines."
                }
            }
            
            # Control flow edge: Program contains Paragraph
            self.edges.append({
                "source": program_name,
                "target": para_id,
                "type": "contains",
                "label": "CONTAINS"
            })
            
            # Detect nested performs: Paragraph -> Paragraph
            perform_pattern = re.compile(r'\bPERFORM\s+([A-Za-z0-9\-]+)\b', re.IGNORECASE)
            for line in para_content:
                # Avoid matching PERFORM UNTIL or PERFORM VARYING if they don't call a target paragraph
                line_upper = line.upper()
                # Simple check to extract paragraph target
                matches = perform_pattern.findall(line)
                for m in matches:
                    # Filter out standard keywords that might be captured
                    if m.upper() not in ["UNTIL", "VARYING", "THRU", "THROUGH"]:
                        target_para_id = f"{program_name}:{m}"
                        self.edges.append({
                            "source": para_id,
                            "target": target_para_id,
                            "type": "performs",
                            "label": "PERFORMS"
                        })
                        
        # Register External CALL relationships
        for ext in external_calls:
            self.edges.append({
                "source": program_name,
                "target": ext,
                "type": "calls",
                "label": "CALLS"
            })
            
        # Register File/DB resources
        for f_name in files_accessed:
            file_node_id = f"FILE_{f_name}"
            if file_node_id not in self.nodes:
                self.nodes[file_node_id] = {
                    "id": file_node_id,
                    "label": f_name,
                    "type": "file",
                    "details": {
                        "description": f"Physical storage file mapped to logic as '{f_name}'."
                    }
                }
            self.edges.append({
                "source": program_name,
                "target": file_node_id,
                "type": "accesses",
                "label": "ACCESSES"
            })
            
        # Parse embedded SQL tables
        if has_sql:
            # Look for DB2 tables referenced in SQL queries: e.g. FROM CUSTOMER, INTO CUSTOMER, UPDATE CUSTOMER
            # Highly basic extractor for tables in SQL SELECT/UPDATE/INSERT
            sql_text = " ".join(lines).upper()
            table_matches = re.findall(r'\bFROM\s+([A-Za-z0-9\-]+)\b|\bUPDATE\s+([A-Za-z0-9\-]+)\b|\bINTO\s+([A-Za-z0-9\-]+)\b', sql_text)
            tables = set()
            for t_tuple in table_matches:
                for t in t_tuple:
                    if t and t not in ["SQL", "TABLE", "CURSOR", "VALUES", "WHERE", "SELECT", "INSERT"]:
                        tables.add(t)
                        
            for t in tables:
                table_node_id = f"DB_{t}"
                if table_node_id not in self.nodes:
                    self.nodes[table_node_id] = {
                        "id": table_node_id,
                        "label": t,
                        "type": "table",
                        "details": {
                            "description": f"Relational database table '{t}' in SQL schema."
                        }
                    }
                self.edges.append({
                    "source": program_name,
                    "target": table_node_id,
                    "type": "queries",
                    "label": "QUERIES"
                })

    def parse_directory(self):
        """Scans the samples directory and parses all COBOL + JCL files into a unified graph."""
        if not self.samples_dir or not os.path.exists(self.samples_dir):
            return {"nodes": [], "edges": []}

        for file in os.listdir(self.samples_dir):
            if file.endswith(('.cbl', '.cob', '.cobol')):
                self.parse_file(os.path.join(self.samples_dir, file))

        # Stitch in JCL orchestrations (Job / Step / Dataset nodes + EXECUTES edges).
        jcl = self._jcl_graph()
        for n in jcl["nodes"]:
            self.nodes.setdefault(n["id"], n)
        for e in jcl["edges"]:
            self.edges.append(e)

        # Clean up any edges that link to non-existent nodes (e.g. external program calls not in the parsed directory)
        cleaned_edges = []
        for edge in self.edges:
            # If the target program doesn't exist in nodes, register a dummy program node so the graph renders beautifully
            if edge["target"] not in self.nodes:
                self.nodes[edge["target"]] = {
                    "id": edge["target"],
                    "label": f"{edge['target']}.CBL",
                    "type": "program",
                    "details": {
                        "loc": 0,
                        "complexity": 0,
                        "riskIndex": 10,
                        "description": f"External program / legacy sub-module '{edge['target']}' (unparsed)."
                    }
                }
            cleaned_edges.append(edge)

        return {
            "nodes": list(self.nodes.values()),
            "edges": cleaned_edges
        }

    def get_system_graph(self):
        """
        Builds a system-level overview graph from the pre-parsed JSON graph files.
        Collects all Program and File nodes, and all CALLS and USES_FILE relations.
        """
        if not os.path.exists(self.custom_kg_dir):
            return self.parse_directory()
            
        nodes = {}
        edges = []
        
        # We only aggregate program JSONs with size > 1500 bytes to keep the overview clean and fast
        for file in os.listdir(self.custom_kg_dir):
            if not file.endswith(".json"):
                continue
            
            file_path = os.path.join(self.custom_kg_dir, file)
            # Only include larger, more interesting programs in the overview
            if os.path.getsize(file_path) < 1500:
                continue
                
            try:
                with open(file_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    
                program_node = None
                for node in data.get("nodes", []):
                    if node.get("type") == "Program":
                        program_node = node
                        break
                
                if not program_node:
                    continue
                    
                p_id = program_node["id"]
                p_label = program_node.get("label", p_id)
                
                # Estimate metrics for this program node from the JSON contents
                loc = len(data.get("nodes", [])) * 8  # proxy
                complexity = len([e for e in data.get("edges", []) if e.get("type") in ["PERFORMS", "JUMPS_TO"]])
                complexity = max(1, complexity)
                
                # Check SQL usage
                has_sql = any(e.get("type") == "WRITES_TO" and "FILE:" not in e.get("target", "") for e in data.get("edges", []))
                
                # Risk calculation
                risk = min(100, int((complexity * 1.5) + (loc * 0.02)))
                if has_sql:
                    risk = min(100, risk + 10)
                
                nodes[p_id] = {
                    "id": p_id,
                    "label": p_label,
                    "type": "program",
                    "details": {
                        "loc": loc,
                        "complexity": complexity,
                        "riskIndex": risk,
                        "hasSql": has_sql,
                        "description": f"Enterprise legacy program {p_label} parsed from corporate codebase."
                    }
                }
                
                for edge in data.get("edges", []):
                    etype = edge.get("type")
                    src = edge.get("source")
                    tgt = edge.get("target")
                    
                    if etype == "CALLS":
                        src_base = src.split(":")[0] if ":" in src else src
                        tgt_base = tgt.split(":")[0] if ":" in tgt else tgt
                        
                        edges.append({
                            "source": src_base,
                            "target": tgt_base,
                            "type": "calls",
                            "label": "CALLS"
                        })
                    elif etype == "USES_FILE" or "FILE:" in tgt:
                        src_base = src.split(":")[0] if ":" in src else src
                        tgt_clean = tgt.replace("FILE:", "")
                        
                        file_id = f"FILE_{tgt_clean}"
                        if file_id not in nodes:
                            nodes[file_id] = {
                                "id": file_id,
                                "label": tgt_clean,
                                "type": "file",
                                "details": {
                                    "description": f"Physical storage file '{tgt_clean}' referenced by {src_base}."
                                }
                            }
                        
                        edges.append({
                            "source": src_base,
                            "target": file_id,
                            "type": "accesses",
                            "label": "ACCESSES"
                        })
            except Exception as e:
                pass
                
        # Fallback to local samples if no external KG files found
        if not nodes:
            return self.parse_directory()

        # De-duplicate edges
        seen_edges = set()
        deduped_edges = []
        for e in edges:
            edge_key = (e["source"], e["target"], e["type"])
            if edge_key not in seen_edges and e["source"] != e["target"]:
                seen_edges.add(edge_key)
                if e["target"] not in nodes and not e["target"].startswith("FILE_"):
                    nodes[e["target"]] = {
                        "id": e["target"],
                        "label": f"{e['target']}.CBL",
                        "type": "program",
                        "details": {
                            "loc": 0,
                            "complexity": 0,
                            "riskIndex": 10,
                            "description": f"External sub-program dependency '{e['target']}' (unparsed)."
                        }
                    }
                deduped_edges.append(e)

        # Stitch JCL orchestrations on top of the corpus-level program graph.
        jcl = self._jcl_graph()
        for n in jcl["nodes"]:
            nodes.setdefault(n["id"], n)
        for e in jcl["edges"]:
            if e["target"] not in nodes and e["type"] == "executes":
                # Step → Program edge where the program isn't in the corpus KG;
                # register a stub so the d3 canvas still renders the linkage.
                nodes[e["target"]] = {
                    "id": e["target"],
                    "label": f"{e['target']}.CBL",
                    "type": "program",
                    "details": {
                        "loc": 0,
                        "complexity": 0,
                        "riskIndex": 10,
                        "description": f"Program '{e['target']}' invoked by JCL but not present in the corpus KG."
                    }
                }
            deduped_edges.append(e)

        return {
            "nodes": list(nodes.values()),
            "edges": deduped_edges
        }

    def _stitch_jcl_upstream(self, focus_program: str, nodes_list, edges_list):
        """Appends any JCL Job/Step/Dataset triples that execute `focus_program`."""
        jcl = self._jcl_graph()
        focus_pg = focus_program.upper().replace(".CBL", "").replace(".COB", "")
        jcl_node_ids = set()
        existing_ids = {n.get("id") for n in nodes_list}

        for e in jcl["edges"]:
            if e["type"] == "executes" and (e["target"] or "").upper() == focus_pg:
                step_id = e["source"]
                jcl_node_ids.add(step_id)
                edges_list.append(e)
                for e2 in jcl["edges"]:
                    if e2["type"] == "contains" and e2["target"] == step_id:
                        jcl_node_ids.add(e2["source"])
                        edges_list.append(e2)
                    if e2["source"] == step_id and e2["type"] == "uses_dd":
                        jcl_node_ids.add(e2["target"])
                        edges_list.append(e2)

        for n in jcl["nodes"]:
            if n["id"] in jcl_node_ids and n["id"] not in existing_ids:
                nodes_list.append(n)

    def get_program_graph(self, program_name):
        """
        Loads the detailed program graph from the pre-parsed JSON files,
        then stitches in any JCL Jobs/Steps that orchestrate this program.
        """
        clean_name = program_name.upper().replace(".CBL", "").replace(".COB", "")

        if not os.path.exists(self.custom_kg_dir):
            # Even without the external KG, still surface JCL upstream.
            empty = {"nodes": [], "edges": []}
            self._stitch_jcl_upstream(clean_name, empty["nodes"], empty["edges"])
            return empty

        # Check standard file variations
        candidates = [
            f"{clean_name}.cbl.json",
            f"{clean_name}.cob.json",
            f"{clean_name}.CBL.json",
            f"{clean_name}.COB.json",
            f"{program_name}.json"
        ]

        target_file = None
        for cand in candidates:
            path = os.path.join(self.custom_kg_dir, cand)
            if os.path.exists(path):
                target_file = path
                break

        if not target_file:
            # Fallback to local live parsing of samples
            sample_path = os.path.join(self.samples_dir, f"{clean_name}.cbl")
            if os.path.exists(sample_path):
                self.nodes = {}
                self.edges = []
                self.parse_file(sample_path)
                nodes_list = list(self.nodes.values())
                edges_list = list(self.edges)
                self._stitch_jcl_upstream(clean_name, nodes_list, edges_list)
                return {"nodes": nodes_list, "edges": edges_list}
            empty = {"nodes": [], "edges": []}
            self._stitch_jcl_upstream(clean_name, empty["nodes"], empty["edges"])
            return empty
            
        with open(target_file, "r", encoding="utf-8") as f:
            data = json.load(f)
            
        nodes = []
        edges = []
        
        seen_nodes = set()
        for node in data.get("nodes", []):
            nid = node.get("id")
            if nid in seen_nodes:
                continue
            seen_nodes.add(nid)
            
            ntype = node.get("type")
            nlabel = node.get("label", nid)
            
            dash_type = "paragraph" if ntype == "Paragraph" else "variable" if ntype == "Variable" else "file" if ntype == "File" else "program"
            
            nodes.append({
                "id": nid,
                "label": nlabel,
                "type": dash_type,
                "details": {
                    "loc": 10 if dash_type == "paragraph" else 0,
                    "complexity": 1 if dash_type == "paragraph" else 0,
                    "description": f"AST AST element parsed by custom parser. Type: {ntype}."
                }
            })
            
        for edge in data.get("edges", []):
            edges.append({
                "source": edge.get("source"),
                "target": edge.get("target"),
                "type": edge.get("type", "contains").lower(),
                "label": edge.get("type", "CONTAINS").upper()
            })

        # JCL upstream stitch — surface any JCL Steps that EXECUTE this program
        # plus their parent Jobs and DD datasets, so the right-hand audit view
        # shows end-to-end orchestration: Job → Step → Program → Paragraphs.
        self._stitch_jcl_upstream(clean_name, nodes, edges)

        return {
            "nodes": nodes,
            "edges": edges
        }

if __name__ == "__main__":
    # Self-test if executed directly
    parser = CobolParser(".")
    print(json.dumps(parser.parse_directory(), indent=2))
