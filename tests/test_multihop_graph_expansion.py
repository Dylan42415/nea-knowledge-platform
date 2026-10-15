"""
Test-driven proof of Programmatic Graph-RAG Traversal (1-Hop & 2-Hop expansion)
and empty stub note filtering.
"""
from pathlib import Path
from src.chat.vault_index import (
    is_stub_note,
    extract_wikilinks_from_note,
    rank_vault_notes,
    expand_graph_neighborhood,
    search_vault_context
)

def test_is_stub_note():
    """Verify that empty/placeholder stubs are flagged and real data notes are preserved."""
    stub1 = {
        "title": "Empty Stub",
        "body": "# Empty Stub\n\n- Linked from [[Some Note]]\n"
    }
    stub2 = {
        "title": "Short Note",
        "body": "No real information here."
    }
    real_note_text = {
        "title": "Real Note",
        "body": "# Real Note\nThis is a substantive note detailing Singapore air quality standards and monitoring regulations."
    }
    real_note_table = {
        "title": "Metric Note",
        "body": "# Metric Note\n| Parameter | Value |\n|---|---|\n| Limit | 5 mg/Nm3 |"
    }

    assert is_stub_note(stub1) is True
    assert is_stub_note(stub2) is True
    assert is_stub_note(real_note_text) is False
    assert is_stub_note(real_note_table) is False

def test_wikilink_heading_anchors_and_subpaths():
    """Verify that wikilinks with section anchors, aliases, and subpaths are properly cleaned."""
    note = {
        "raw_content": "See [[Air Quality#Standards (2020)|Standards]], [[concepts/PM25#Section]], and [[Standard Note]]."
    }
    targets = extract_wikilinks_from_note(note)
    assert targets == ["Air Quality", "PM25", "Standard Note"]

def test_null_aliases_does_not_crash(tmp_path: Path):
    """Verify that notes with null/missing frontmatter aliases do not cause TypeError."""
    vault_dir = tmp_path / "vault_null_aliases"
    vault_dir.mkdir(parents=True, exist_ok=True)

    note = vault_dir / "null_alias.md"
    note.write_text("""---
title: Null Alias Note
aliases:
---
# Null Alias Note
Substantive text content that describes environmental monitoring standards.
""", encoding="utf-8")

    # expand_graph_neighborhood and search_vault_context must not crash
    res = expand_graph_neighborhood("Null Alias Note", vault_dir)
    assert len(res) == 1
    assert res[0]["note"]["title"] == "Null Alias Note"

def test_2hop_graph_traversal_reaches_leaf_node(tmp_path: Path):
    """
    Test that a 2-hop query where the prompt lacks intermediate or leaf keywords
    successfully traverses the graph and retrieves the target leaf node.
    
    Graph Topology:
      [Jurong Petrochemical Complex] (Seed)
             │
             ▼ (Hop 1)
      [Volatile Organic Compounds (VOCs)] (Bridge)
             │
             ▼ (Hop 2)
      [Benzene Ambient Standards] (Leaf - contains 0.28 ppb)
      
      [Empty Stub Placeholder] (Stub linked from Seed - must be filtered out)
    """
    vault_dir = tmp_path / "vault"
    concepts_dir = vault_dir / "concepts"
    concepts_dir.mkdir(parents=True, exist_ok=True)

    # Note A: Seed Node (Mentions Jurong, emits VOCs, links to stub)
    note_a = concepts_dir / "jurong_petrochemical_complex.md"
    note_a.write_text("""---
title: Jurong Petrochemical Complex
type: Location
source_document: industrial_masterplan.pdf
---
# Jurong Petrochemical Complex

## Summary
The Jurong Petrochemical Complex hosts multiple refinery and chemical manufacturing facilities.
Facilities on this island emit [[Volatile Organic Compounds (VOCs)]] and maintain a placeholder link to [[Empty Stub Placeholder]].
""", encoding="utf-8")

    # Note B: Bridge Node (Mentions VOCs, links to Benzene standards)
    note_b = concepts_dir / "volatile_organic_compounds.md"
    note_b.write_text("""---
title: Volatile Organic Compounds (VOCs)
type: Concept
source_document: air_regulations.pdf
---
# Volatile Organic Compounds (VOCs)

## Summary
Volatile organic compounds are gaseous chemicals monitored under national air quality programs.
The key carcinogenic hydrocarbon regulated under this category is [[Benzene Ambient Standards]].
""", encoding="utf-8")

    # Note C: Leaf Node (Contains exact target metric, NO mention of Jurong, industrial, or emission)
    note_c = concepts_dir / "benzene_ambient_standards.md"
    note_c.write_text("""---
title: Benzene Ambient Standards
type: Concept
source_document: soe_report_2020.pdf
source_location: p. 14
---
# Benzene Ambient Standards

## Summary
Benzene is monitored to protect human health against toxic carcinogenic risk.
The 2020 annual mean concentration was recorded at 0.28 ppb, complying with national environmental thresholds.
""", encoding="utf-8")

    # Note D: Empty Stub Node (Must NOT crowd out real notes)
    note_d = concepts_dir / "empty_stub_placeholder.md"
    note_d.write_text("""---
title: Empty Stub Placeholder
type: Concept
---
# Empty Stub Placeholder
- Linked from [[Jurong Petrochemical Complex]]
""", encoding="utf-8")

    query = "What industrial emission guidelines apply to Jurong Petrochemical Complex?"

    # 1. Verify that pure BM25 fails to place the Leaf Node in the top 1
    bm25_results = rank_vault_notes(query, vault_dir, top_k=5)
    bm25_titles = [note["title"] for _, note in bm25_results]
    assert "Jurong Petrochemical Complex" in bm25_titles
    # Leaf note has 0 keyword matches with the query, so it cannot be rank #1
    assert bm25_results[0][1]["title"] != "Benzene Ambient Standards"

    # 2. Verify that expand_graph_neighborhood programmatically reaches the 2-hop leaf
    expanded = expand_graph_neighborhood(query, vault_dir, top_seeds=1, max_depth=2, max_total_notes=5)
    
    titles_retrieved = [item["note"]["title"] for item in expanded]
    hops_retrieved = {item["note"]["title"]: item["hop"] for item in expanded}
    
    # Assert Seed is Hop 0
    assert "Jurong Petrochemical Complex" in titles_retrieved
    assert hops_retrieved["Jurong Petrochemical Complex"] == 0

    # Assert Bridge is Hop 1
    assert "Volatile Organic Compounds (VOCs)" in titles_retrieved
    assert hops_retrieved["Volatile Organic Compounds (VOCs)"] == 1

    # Assert Leaf is Hop 2
    assert "Benzene Ambient Standards" in titles_retrieved
    assert hops_retrieved["Benzene Ambient Standards"] == 2

    # Assert Empty Stub was filtered out and NOT collected
    assert "Empty Stub Placeholder" not in titles_retrieved

    # 3. Verify that search_vault_context formats graph provenance and reaches target data
    context = search_vault_context(query, vault_dir, max_notes=5, max_depth=2, top_seeds=1)
    assert "--- SEED NOTE (Hop 0): [[Jurong Petrochemical Complex]]" in context
    assert "--- GRAPH NEIGHBOR (Hop 1): [[Volatile Organic Compounds (VOCs)]]" in context
    assert "--- GRAPH LEAF (Hop 2): [[Benzene Ambient Standards]]" in context
    assert "0.28 ppb" in context
    assert "Graph Provenance Path: [[Jurong Petrochemical Complex]] → [[Volatile Organic Compounds (VOCs)]] → [[Benzene Ambient Standards]]" in context

def test_backlink_canonicalization_and_cycle_safety(tmp_path: Path):
    """
    Verify:
    1. Incoming backlinks resolve even when linking to an alias of the target note.
    2. Cyclic graphs (A <-> B) terminate safely without duplicates.
    3. Correct path provenance direction from seed.
    """
    vault_dir = tmp_path / "vault_cycles"
    vault_dir.mkdir(parents=True, exist_ok=True)

    # Note A links to Note B
    (vault_dir / "note_a.md").write_text("""---
title: Note Alpha
---
# Note Alpha
Alpha links to [[Note Beta]] in a bidirectional relationship.
""", encoding="utf-8")

    # Note B links back to Note A (Cycle: A <-> B)
    (vault_dir / "note_b.md").write_text("""---
title: Note Beta
aliases: [BetaAlias]
---
# Note Beta
Beta links back to [[Note Alpha]] creating a closed loop.
""", encoding="utf-8")

    # Note C links to Note B using its alias [[BetaAlias]]
    (vault_dir / "note_c.md").write_text("""---
title: Note Gamma
---
# Note Gamma
Gamma provides additional context and references [[BetaAlias]].
""", encoding="utf-8")

    # Query matching Note Beta
    res = expand_graph_neighborhood("Note Beta", vault_dir, top_seeds=1, max_depth=2, max_total_notes=5)
    retrieved_titles = [x["note"]["title"] for x in res]
    
    # 1. Cycle Safety: No duplicate entries
    assert len(retrieved_titles) == len(set(retrieved_titles))
    assert "Note Beta" in retrieved_titles
    assert "Note Alpha" in retrieved_titles
    
    # 2. Backlink Alias Resolution: Note Gamma resolved as backlink of Note Beta via alias
    assert "Note Gamma" in retrieved_titles
    
    # 3. Path provenance for backlink originates from Seed (Note Beta)
    gamma_item = next(x for x in res if x["note"]["title"] == "Note Gamma")
    assert gamma_item["path"] == ["Note Beta", "Note Gamma"]
    assert "Backlinked from [[Note Gamma]]" in gamma_item["relation"]
