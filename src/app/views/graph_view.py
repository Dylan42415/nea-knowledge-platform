import os
import sys
import re
import math
import streamlit as st
from streamlit_agraph import agraph, Node, Edge, Config
import yaml
from pathlib import Path

# Ensure project root is in sys.path
_current = Path(__file__).resolve()
for _p in [_current] + list(_current.parents):
    if (_p / "src").is_dir():
        if str(_p) not in sys.path:
            sys.path.insert(0, str(_p))
        break

from src.config import VAULT_ROOT
from src.vault_writer.note_generator import sanitize_filename
from src.chat.chat_engine import generate_vault_response
from src.workspace.workspace_manager import get_scoped_notes
from src.workspace.synthesis_engine import get_existing_synthesis, synthesize_subject_cross_links
from src.chat.vault_index import parse_note

def parse_frontmatter(content: str) -> dict:
    """Parse YAML frontmatter from markdown content."""
    if content.startswith('---'):
        parts = content.split('---', 2)
        if len(parts) >= 3:
            try:
                return yaml.safe_load(parts[1]) or {}
            except Exception:
                pass
    return {}

def resolve_target_ids(raw_target: str, title_to_ids: dict, note_info: list, id_to_note: dict, vault_dir: Path) -> list[str]:
    """
    Universal Target Link Resolver for all present and future processed files.
    Matches exact titles, lowercase, sanitized stems, stripped parentheses (e.g., NEA), frontmatter aliases,
    disk-file lookups, and creates dynamic virtual fallback nodes ONLY if no file exists anywhere on disk.
    """
    clean_target = raw_target.split('|')[0].strip()
    if not clean_target:
        return []

    # 1. Exact match
    if clean_target in title_to_ids:
        return title_to_ids[clean_target]

    # 2. Lowercase match
    if clean_target.lower() in title_to_ids:
        return title_to_ids[clean_target.lower()]
    
    # 3. Sanitize filename match
    sanitized = sanitize_filename(clean_target)
    if sanitized in title_to_ids:
        return title_to_ids[sanitized]

    # 4. Stripped parenthesis match (e.g. 'National Environment Agency' -> 'National Environment Agency (NEA)')
    stripped = re.sub(r'\s*\([^)]*\)', '', clean_target).strip()
    if stripped in title_to_ids:
        return title_to_ids[stripped]
    if stripped.lower() in title_to_ids:
        return title_to_ids[stripped.lower()]

    # 5. Normalized alphanumeric matching
    norm_target = re.sub(r'[^a-z0-9]', '', clean_target.lower())
    for key, ids in title_to_ids.items():
        if re.sub(r'[^a-z0-9]', '', key.lower()) == norm_target:
            return ids

    # 6. Check existing note_info titles before creating virtual node
    for n in note_info:
        if n["title"].lower() == clean_target.lower() or sanitize_filename(n["title"]).lower() == sanitized.lower():
            return [n["id"]]

    # 7. DISK FILE LOOKUP: If target note exists on disk in vault_dir, load REAL file!
    if vault_dir and vault_dir.exists():
        for candidate_file in vault_dir.rglob("*.md"):
            if candidate_file.stem.lower() in (clean_target.lower(), sanitized.lower(), stripped.lower()):
                try:
                    parsed = parse_note(candidate_file)
                    ntype = parsed.get("type", "concept").lower()
                    real_id = f"{ntype}/{candidate_file.stem}"
                    
                    real_note = {
                        "id": real_id,
                        "title": parsed.get("title", candidate_file.stem),
                        "type": ntype,
                        "content": parsed.get("body", parsed.get("raw_content", "")),
                        "filepath": str(candidate_file)
                    }
                    
                    if real_id not in id_to_note:
                        note_info.append(real_note)
                        id_to_note[real_id] = real_note
                        
                    title_to_ids[clean_target] = [real_id]
                    title_to_ids[clean_target.lower()] = [real_id]
                    title_to_ids[candidate_file.stem] = [real_id]
                    return [real_id]
                except Exception:
                    pass

    # 8. Virtual Node Fallback Creation (only if file truly does not exist anywhere on disk)
    virt_id = f"concept/{sanitized if sanitized else 'target'}"
    if virt_id not in id_to_note:
        virt_note = {
            "id": virt_id,
            "title": clean_target,
            "type": "concept",
            "content": f"# {clean_target}\n\n## Summary\n{clean_target} is a recognized entity linked within the Knowledge Graph.\n",
            "filepath": f"virtual/{clean_target}.md"
        }
        note_info.append(virt_note)
        id_to_note[virt_id] = virt_note
        title_to_ids[clean_target] = [virt_id]
        title_to_ids[clean_target.lower()] = [virt_id]

    return [virt_id]

def compute_soundscribe_layout(note_info: list[dict], edges: list, arc_gap: float = 380.0, min_dist: float = 420.0) -> tuple[dict[str, dict[str, float]], str]:
    """
    Soundscribe Concentric Ring Layout & 80-Iteration Pairwise Repulsion Engine.
    Positions root node at origin (0, 0) and arranges all other nodes into wide staggered concentric rings
    with an 80-iteration repulsion pass ensuring a minimum spacing of min_dist between nodes.
    """
    degree: dict[str, int] = {}
    neighbors: dict[str, set[str]] = {}

    for note in note_info:
        nid = note["id"]
        degree[nid] = 0
        neighbors[nid] = set()

    for edge in edges:
        src = getattr(edge, 'source', getattr(edge, 'from', None))
        tgt = getattr(edge, 'target', getattr(edge, 'to', None))
        if src in degree and tgt in degree:
            degree[src] += 1
            degree[tgt] += 1
            neighbors[src].add(tgt)
            neighbors[tgt].add(src)

    sorted_notes = sorted(note_info, key=lambda n: degree.get(n["id"], 0), reverse=True)
    root_id = sorted_notes[0]["id"] if sorted_notes else ""

    non_root_notes = [n for n in sorted_notes if n["id"] != root_id]

    positions: dict[str, dict[str, float]] = {}
    if root_id:
        positions[root_id] = {"x": 0.0, "y": 0.0}

    ring_radii = [480.0, 960.0, 1440.0, 1920.0, 2400.0]
    ring_caps = [max(1, int((2 * math.pi * r) / arc_gap)) for r in ring_radii]

    ring_idx = 0
    slot_in_ring = 0

    for note in non_root_notes:
        nid = note["id"]
        radius = ring_radii[min(ring_idx, len(ring_radii) - 1)]
        cap = ring_caps[min(ring_idx, len(ring_caps) - 1)]
        offset = (math.pi / cap) if (ring_idx % 2 == 1) else 0.0
        angle = (slot_in_ring / cap) * 2.0 * math.pi - (math.pi / 2.0) + offset

        positions[nid] = {
            "x": math.cos(angle) * radius,
            "y": math.sin(angle) * radius
        }

        slot_in_ring += 1
        if slot_in_ring >= cap:
            ring_idx += 1
            slot_in_ring = 0

    all_ids = list(positions.keys())
    ITERATIONS = 80

    for _ in range(ITERATIONS):
        for i in range(len(all_ids)):
            for j in range(i + 1, len(all_ids)):
                id_a = all_ids[i]
                id_b = all_ids[j]
                pos_a = positions[id_a]
                pos_b = positions[id_b]

                dx = pos_b["x"] - pos_a["x"]
                dy = pos_b["y"] - pos_a["y"]
                dist = math.sqrt(dx * dx + dy * dy) or 1.0

                if dist >= min_dist:
                    continue

                push = (min_dist - dist) * 0.5
                nx = (dx / dist) * push
                ny = (dy / dist) * push

                if id_b != root_id:
                    pos_b["x"] += nx
                    pos_b["y"] += ny
                if id_a != root_id:
                    pos_a["x"] -= nx
                    pos_a["y"] -= ny

    return positions, root_id


def render_graph_page():
    """Renders interactive knowledge graph with independent Wiki Reader and AI Cross-Lecture Synthesis Engine."""
    vault_dir = Path(VAULT_ROOT)
    active_scope = st.session_state.get("active_study_scope", "All Files (Global Vault)")

    st.title("🕸️ Interactive Knowledge Graph")
    st.caption(f"🎯 **Active Scope**: `{active_scope}` | Direct Obsidian Relationship Extractor & Soundscribe Concentric Layout")

    scoped_notes = get_scoped_notes(vault_dir, active_scope)
    if not scoped_notes:
        st.info(f"No notes found in scope `{active_scope}`. Record a lecture or upload data to populate this scope.")
        return

    type_colors = {
        "dataset": "#3b82f6",     # Blue (Lectures)
        "concept": "#22c55e",     # Green (Academic Concepts)
        "location": "#f97316",    # Orange (Locations)
        "organization": "#a855f7",# Purple (Standards)
        "unknown": "#64748b"      # Gray
    }

    rel_predicate_pattern = re.compile(r'-\s*\*\*([A-Za-z0-9_]+)\*\*\s*→\s*\[\[(.*?)\]\]')
    wikilink_pattern = re.compile(r'\[\[(.*?)\]\]')

    note_info = []
    title_to_ids: dict[str, list[str]] = {}
    id_to_note: dict[str, dict] = {}

    def _add_mapping(key: str, val: str):
        if not key:
            return
        clean_k = key.strip()
        if clean_k not in title_to_ids:
            title_to_ids[clean_k] = []
        if val not in title_to_ids[clean_k]:
            title_to_ids[clean_k].append(val)

    for note_item in scoped_notes:
        filepath = Path(note_item["filepath"])
        safe_stem = filepath.stem
        content = note_item["raw_content"]
        metadata = parse_frontmatter(content)
        title = metadata.get("title", note_item.get("title", safe_stem))
        ntype = metadata.get("type", note_item.get("type", "concept")).lower()

        node_id = f"{ntype}/{safe_stem}"

        _add_mapping(node_id, node_id)
        _add_mapping(safe_stem, node_id)
        _add_mapping(safe_stem.lower(), node_id)
        _add_mapping(title, node_id)
        _add_mapping(title.lower(), node_id)
        _add_mapping(sanitize_filename(title), node_id)

        stripped_title = re.sub(r'\s*\([^)]*\)', '', title).strip()
        stripped_stem = re.sub(r'\s*\([^)]*\)', '', safe_stem).strip()
        _add_mapping(stripped_title, node_id)
        _add_mapping(stripped_title.lower(), node_id)
        _add_mapping(stripped_stem, node_id)
        _add_mapping(stripped_stem.lower(), node_id)

        aliases = metadata.get("aliases", [])
        if isinstance(aliases, list):
            for alias in aliases:
                _add_mapping(str(alias), node_id)
                _add_mapping(str(alias).lower(), node_id)

        n_dict = {
            "id": node_id,
            "title": title,
            "type": ntype,
            "content": note_item.get("body", content),
            "filepath": str(filepath)
        }
        note_info.append(n_dict)
        if node_id not in id_to_note:
            id_to_note[node_id] = n_dict

    col_controls, col_graph = st.columns([1, 2.8])

    with col_controls:
        st.subheader("Graph Controls")
        
        all_titles = sorted(list(set(n["title"] for n in note_info)))

        def _on_select_change():
            sel = st.session_state.get("graph_node_select_box")
            if sel and sel != "-- None Selected --":
                st.session_state["selected_concept_title"] = sel
                st.session_state["reader_note_title"] = sel

        current_sel_idx = 0
        if "selected_concept_title" in st.session_state and st.session_state["selected_concept_title"] in all_titles:
            current_sel_idx = all_titles.index(st.session_state["selected_concept_title"]) + 1

        selected_title = st.selectbox(
            "Select Concept Node to Focus Graph",
            ["-- None Selected --"] + all_titles,
            index=current_sel_idx,
            key="graph_node_select_box",
            on_change=_on_select_change
        )
        if selected_title != "-- None Selected --":
            st.session_state["selected_concept_title"] = selected_title
            if "reader_note_title" not in st.session_state:
                st.session_state["reader_note_title"] = selected_title

        focus_subgraph = st.checkbox("🔍 Isolate Selected Sub-graph", value=True)
        include_in_text = st.checkbox("Include General In-Text Mentions", value=False)
        use_soundscribe = st.checkbox("⭐ Soundscribe Concentric Layout", value=True)
        
        node_type_filter = st.selectbox("Filter Category", ["All", "Concept", "Dataset", "Organization", "Location"])
        search_node = st.text_input("Search Concept", "", key="graph_search")

        # Subject AI Synthesis Button
        is_subject_scope = active_scope.startswith("Subject: ")
        subject_name = active_scope.replace("Subject: ", "").strip() if is_subject_scope else ""
        
        if is_subject_scope:
            st.markdown("---")
            st.markdown("##### 🔄 AI Cross-Lecture Synthesis")
            def _trigger_synthesis_graph(s_name=subject_name):
                with st.spinner(f"Synthesizing cross-lecture bridges for {s_name}..."):
                    res = synthesize_subject_cross_links(vault_dir, s_name)
                    st.toast(f"Synthesized {len(res.get('cross_bridges', []))} bridges!")

            st.button("🔄 Synthesize Subject Bridges", key="btn_syn_graph", use_container_width=True, on_click=_trigger_synthesis_graph)

    # Pass 2: Build Graph Edges EXCLUSIVELY from Pipeline Typed Relationships
    edges = []
    added_edges = set()

    for note in list(note_info):
        source_id = note["id"]
        content = note["content"]

        explicit_matches = rel_predicate_pattern.findall(content)
        explicit_targets = set()

        for predicate, raw_target in explicit_matches:
            target_name = raw_target.split('|')[0].strip()
            explicit_targets.add(target_name.lower())

            target_ids = resolve_target_ids(target_name, title_to_ids, note_info, id_to_note, vault_dir)
            for target_id in target_ids:
                if target_id != source_id:
                    edge_pair = (source_id, target_id, predicate)
                    if edge_pair not in added_edges:
                        added_edges.add(edge_pair)
                        edges.append(Edge(
                            source=source_id,
                            target=target_id,
                            label=predicate,
                            color="#0ea5e9"
                        ))

        if include_in_text:
            all_links = wikilink_pattern.findall(content)
            for link in all_links:
                raw_target = link.split('|')[0].strip()
                if raw_target.lower() in explicit_targets:
                    continue

                rel_label = link.split('|')[1].strip() if '|' in link else "LINKED_TO"
                target_ids = resolve_target_ids(raw_target, title_to_ids, note_info, id_to_note, vault_dir)

                for target_id in target_ids:
                    if target_id != source_id:
                        edge_pair = (source_id, target_id, rel_label)
                        if edge_pair not in added_edges:
                            added_edges.add(edge_pair)
                            edges.append(Edge(
                                source=source_id,
                                target=target_id,
                                label=rel_label,
                                color="#475569"
                            ))

    # Pass 2b: Add Synthesized Cross-Lecture Bridges if Subject Scope
    subject_synthesis = {}
    if is_subject_scope:
        subject_synthesis = get_existing_synthesis(vault_dir, subject_name)
        bridges = subject_synthesis.get("cross_bridges", [])
        for bridge in bridges:
            src_name = bridge.get("source_concept", "")
            tgt_name = bridge.get("target_concept", "")
            rel = bridge.get("relationship", "SYNTHESIZED_LINK")
            
            src_ids = resolve_target_ids(src_name, title_to_ids, note_info, id_to_note, vault_dir)
            tgt_ids = resolve_target_ids(tgt_name, title_to_ids, note_info, id_to_note, vault_dir)
            
            for s_id in src_ids:
                for t_id in tgt_ids:
                    if s_id != t_id:
                        edge_pair = (s_id, t_id, f"✨ {rel}")
                        if edge_pair not in added_edges:
                            added_edges.add(edge_pair)
                            edges.append(Edge(
                                source=s_id,
                                target=t_id,
                                label=f"✨ {rel}",
                                color="#a855f7"
                            ))

    layout_positions, root_id = compute_soundscribe_layout(note_info, edges)

    selected_node_id = None
    if selected_title and selected_title != "-- None Selected --":
        for n in note_info:
            if n["title"] == selected_title:
                selected_node_id = n["id"]
                break

    neighbor_node_ids = set()
    related_connections = []

    if selected_node_id:
        neighbor_node_ids.add(selected_node_id)
        for edge in edges:
            src = getattr(edge, 'source', getattr(edge, 'from', None))
            tgt = getattr(edge, 'target', getattr(edge, 'to', None))
            lbl = getattr(edge, 'label', 'LINKED_TO')

            if src == selected_node_id:
                neighbor_node_ids.add(tgt)
                src_n = id_to_note.get(src, {})
                tgt_n = id_to_note.get(tgt, {})
                related_connections.append({
                    "source": src_n.get("title", src),
                    "target": tgt_n.get("title", tgt),
                    "predicate": lbl,
                    "target_id": tgt,
                    "target_title": tgt_n.get("title", tgt),
                    "direction": "outgoing"
                })
            elif tgt == selected_node_id:
                neighbor_node_ids.add(src)
                src_n = id_to_note.get(src, {})
                tgt_n = id_to_note.get(tgt, {})
                related_connections.append({
                    "source": src_n.get("title", src),
                    "target": tgt_n.get("title", tgt),
                    "predicate": lbl,
                    "target_id": src,
                    "target_title": src_n.get("title", src),
                    "direction": "incoming"
                })

    nodes = []
    filtered_edges = []
    node_ids = set()
    node_labels = {}
    added_node_ids = set()

    for note in note_info:
        ntype = note["type"]
        title = note["title"]
        node_id = note["id"]

        if node_type_filter != "All" and ntype != node_type_filter.lower():
            continue

        if search_node and search_node.lower() not in title.lower():
            continue

        if focus_subgraph and selected_node_id and node_id not in neighbor_node_ids:
            continue

        if node_id in added_node_ids:
            continue

        added_node_ids.add(node_id)
        node_ids.add(node_id)
        node_labels[node_id] = title

        display_label = title[:25] + "..." if len(title) > 25 else title
        pos = layout_positions.get(node_id, {"x": 0, "y": 0})
        is_root = (node_id == root_id)
        is_selected = (node_id == selected_node_id)

        node_color = "#38bdf8" if is_selected else ("#f59e0b" if is_root else type_colors.get(ntype, type_colors["unknown"]))
        node_size = 42 if is_selected else (36 if is_root else 26)

        nodes.append(Node(
            id=node_id,
            label=f"🎯 {display_label}" if is_selected else (f"⭐ {display_label}" if is_root else display_label),
            size=node_size,
            x=pos["x"] if use_soundscribe else None,
            y=pos["y"] if use_soundscribe else None,
            color=node_color,
            font={"color": "#ffffff", "size": 14 if is_selected else 13, "strokeWidth": 2, "strokeColor": "#0f172a"},
            title=f"{'🎯 Selected' if is_selected else ('⭐ Root Concept' if is_root else ntype.capitalize())}: {title}"
        ))

    for edge in edges:
        src = getattr(edge, 'source', getattr(edge, 'from', None))
        tgt = getattr(edge, 'target', getattr(edge, 'to', None))
        if src and tgt and src in node_ids and tgt in node_ids:
            filtered_edges.append(edge)

    if use_soundscribe:
        physics_config = {"enabled": False}
        is_hierarchical = False
    else:
        physics_config = {
            "enabled": True,
            "forceAtlas2Based": {
                "gravitationalConstant": -220,
                "centralGravity": 0.005,
                "springLength": 250,
                "springConstant": 0.06,
                "damping": 0.4
            },
            "solver": "forceAtlas2Based"
        }
        is_hierarchical = False

    with col_graph:
        config = Config(
            width=950,
            height=700,
            directed=True,
            physics=physics_config,
            hierarchical=is_hierarchical,
            nodeHighlightBehavior=True,
            highlightColor="#38bdf8",
            collapsible=False,
            node={
                'labelProperty': 'label',
                'font': {'size': 13, 'color': '#ffffff', 'strokeWidth': 2, 'strokeColor': '#0f172a'}
            },
            link={
                'labelProperty': 'label',
                'renderLabel': True,
                'font': {'size': 11, 'color': '#38bdf8', 'strokeWidth': 2, 'strokeColor': '#0f172a'}
            }
        )

        clicked_node_id = agraph(nodes=nodes, edges=filtered_edges, config=config)

    if clicked_node_id and clicked_node_id in id_to_note:
        st.session_state["selected_concept_title"] = id_to_note[clicked_node_id]["title"]
        st.session_state["reader_note_title"] = id_to_note[clicked_node_id]["title"]

    st.markdown("---")

    reader_title = st.session_state.get("reader_note_title", selected_title if selected_title != "-- None Selected --" else "")
    reader_node = None
    if reader_title:
        for n in note_info:
            if n["title"].lower() == reader_title.lower():
                reader_node = n
                break

    if not reader_node and selected_node_id:
        reader_node = id_to_note.get(selected_node_id)

    # Deterministic On-Click Callbacks for Buttons
    def _set_reader_note(target_title: str):
        st.session_state["reader_note_title"] = target_title

    def _set_focus_and_reader(target_title: str):
        st.session_state["selected_concept_title"] = target_title
        st.session_state["reader_note_title"] = target_title

    if reader_node:
        is_viewing_same_as_graph = (selected_node_id and reader_node["id"] == selected_node_id)
        
        st.subheader(f"📌 Reading Wiki Note: [[{reader_node['title']}]]")
        if not is_viewing_same_as_graph and selected_title != "-- None Selected --":
            st.caption(f"ℹ️ Visual Graph is currently focused on **[[{selected_title}]]**. You are reading **[[{reader_node['title']}]]** without changing the graph layout.")
            col_re1, col_re2 = st.columns([2, 1])
            with col_re2:
                st.button(
                    f"🎯 Re-focus Graph to [[{reader_node['title']}]]",
                    key="btn_refocus_main",
                    type="primary",
                    use_container_width=True,
                    on_click=_set_focus_and_reader,
                    args=(reader_node['title'],)
                )
        
        tab_list = [
            f"📄 Wiki Note Content ({reader_node['type'].capitalize()})",
            f"🔗 Related Concepts ({len(related_connections)})",
            f"💬 Ask AI about {reader_node['title']}",
            "💬 Scope Vault Assistant"
        ]
        if is_subject_scope:
            tab_list.insert(2, "✨ Subject AI Synthesis")

        tab_objects = st.tabs(tab_list)

        with tab_objects[0]:
            st.markdown(reader_node["content"])

        with tab_objects[1]:
            st.markdown(f"### Direct Connections for [[{selected_title if selected_title != '-- None Selected --' else reader_node['title']}]]")
            if not related_connections:
                st.info("No direct relationships extracted for this concept node yet.")
            else:
                for idx, rel in enumerate(related_connections):
                    col_r1, col_r2, col_r3 = st.columns([3, 1.2, 1.2])
                    with col_r1:
                        if rel["direction"] == "outgoing":
                            st.markdown(f"👉 **[[{rel['source']}]]** `-- [{rel['predicate']}] -->` **[[{rel['target']}]]**")
                        else:
                            st.markdown(f"👈 **[[{rel['source']}]]** `-- [{rel['predicate']}] -->` **[[{rel['target']}]]**")
                    with col_r2:
                        st.button(
                            "📖 Read Wiki",
                            key=f"btn_read_{idx}_{sanitize_filename(rel['target_id'])}",
                            use_container_width=True,
                            on_click=_set_reader_note,
                            args=(rel['target_title'],)
                        )
                    with col_r3:
                        st.button(
                            "🎯 Focus Graph",
                            key=f"btn_focus_{idx}_{sanitize_filename(rel['target_id'])}",
                            use_container_width=True,
                            on_click=_set_focus_and_reader,
                            args=(rel['target_title'],)
                        )

        if is_subject_scope:
            with tab_objects[2]:
                st.markdown(f"### ✨ AI Cross-Lecture Synthesis for `{subject_name}`")
                if not subject_synthesis or not subject_synthesis.get("cross_bridges"):
                    st.info("No synthesis generated for this subject collection yet. Click **🔄 Synthesize Subject Bridges** in Graph Controls or Workspace Manager to discover cross-lecture links!")
                else:
                    st.markdown(subject_synthesis.get("synthesis_summary", ""))
                    st.markdown("#### Discovered Cross-Lecture Bridges:")
                    for b in subject_synthesis.get("cross_bridges", []):
                        with st.container(border=True):
                            st.markdown(f"✨ **[[{b.get('source_concept')}]]** `-- [{b.get('relationship')}] -->` **[[{b.get('target_concept')}]]**")
                            st.caption(f"**Explanation**: {b.get('explanation')}")
                            if b.get('source_file') and b.get('target_file'):
                                st.caption(f"📍 **Bridges**: `{b.get('source_file')}` ↔ `{b.get('target_file')}`")

        chat_tab = tab_objects[3 if is_subject_scope else 2]
        global_chat_tab = tab_objects[4 if is_subject_scope else 3]

        with chat_tab:
            st.info(f"Targeted Q&A scoped directly to concept **[[{reader_node['title']}]]**.")
            
            if "node_chat_history" not in st.session_state:
                st.session_state.node_chat_history = {}
                
            node_key = reader_node["title"]
            if node_key not in st.session_state.node_chat_history:
                st.session_state.node_chat_history[node_key] = [
                    {"role": "assistant", "content": f"Hello! Ask me any question specifically about **[[{reader_node['title']}]]** or how it relates to other concepts in `{active_scope}`."}
                ]

            for msg in st.session_state.node_chat_history[node_key]:
                with st.chat_message(msg["role"]):
                    st.markdown(msg["content"])

            node_prompt = st.chat_input(f"Ask AI about {reader_node['title']}...", key="node_chat_input")
            if node_prompt:
                st.session_state.node_chat_history[node_key].append({"role": "user", "content": node_prompt})
                with st.chat_message("user"):
                    st.markdown(node_prompt)

                with st.chat_message("assistant"):
                    with st.spinner("Analyzing node context..."):
                        scoped_query = f"Regarding {reader_node['title']}: {node_prompt}"
                        messages_payload = st.session_state.node_chat_history[node_key][:-1] + [{"role": "user", "content": scoped_query}]
                        ans = generate_vault_response(messages_payload)
                        st.markdown(ans)
                        st.session_state.node_chat_history[node_key].append({"role": "assistant", "content": ans})

        with global_chat_tab:
            _render_global_chat_tab(active_scope)

    else:
        st.info("💡 Click any node on the graph above or select a concept from the dropdown to inspect note details, explore related nodes, and ask AI questions!")
        _render_global_chat_tab(active_scope)

def _render_global_chat_tab(active_scope: str):
    st.subheader(f"💬 Scope Assistant ({active_scope})")
    st.caption("Ask questions across lectures and concepts in the currently active study scope.")

    if "global_chat_history" not in st.session_state:
        st.session_state.global_chat_history = [
            {"role": "assistant", "content": f"Welcome! I am your Assistant for `{active_scope}`. Ask me anything about these concepts or topics!"}
        ]

    for msg in st.session_state.global_chat_history:
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])

    user_query = st.chat_input(f"Ask a question in {active_scope}...", key="global_chat_input")
    if user_query:
        st.session_state.global_chat_history.append({"role": "user", "content": user_query})
        with st.chat_message("user"):
            st.markdown(user_query)

        with st.chat_message("assistant"):
            with st.spinner("Searching scoped knowledge graph & synthesizing answer..."):
                resp = generate_vault_response(st.session_state.global_chat_history)
                st.markdown(resp)
                st.session_state.global_chat_history.append({"role": "assistant", "content": resp})

if __name__ == "__main__":
    render_graph_page()
