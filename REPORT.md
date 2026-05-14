## 1. What & Why

shap-to-report is a RAG LLM pipeline that turns spacecraft anomaly detection output into structured diagnostic reports. The intended user is a spacecraft operations engineer who receives a SHAP (SHapley Additive exPlanations) attribution chart from an onboard anomaly detector and needs a natural language situational assessment; grounded in real regulatory frameworks (EU AI Act, NASA NPR 7150.2D, FAA AI Roadmap) and historical mission precedents.

This is a prototype for the LLM reasoning layer in my CPSC 491 capstone project. The anomaly detector already exists; this project builds the explanation layer on top of it.

What makes the AI behavior hard to get right: 

    The model must cite real regulatory language without hallucinating it, use observational language only (no prescriptive action verbs like "verify" or "recommend"). Diffuse attribution (low Gini coefficient) should produce hedged, low confidence reports. Every claim must trace back to a retrieved chunk(s). Getting all four of these right simultaneously, across anomaly archetypes ranging from concentrated single channel faults to diffuse multi channel noise is the challenge.

---

## 2. Iterations

###  Mock Baseline V1

**Change:** Established the full pipeline with a deterministic MockBackend. No real LLM calls. The backend cycles through three fixed report templates and fires a structured refusal for event IDs ending in 3, 6, or 9.

**Motivating example:** Event evt_005 (diffuse, Gini=0.08) exposed the gap: the mock returned attribution_concentration = 0.21 regardless of the actual Gini value, confirming the pipeline was not yet event aware.

**Delta:** Mock baseline on 10 events: mean composite **0.57**. schema_valid 1.00, no_prescriptive_verbs 1.00, channel_grounded 0.14, top_driver_correct 0.14. Low channel/top driver scores are by design: the mock returns fixed templates.

**Conclusion:** The low scores confirm the eval harness correctly catches when the model is not event aware. Validator checks pass at 1.00, validating OutputValidator logic. Next: wire the OpenAI backend with real SHAP prompting.

###  Primary Feature Selection and Explanation Grounding V2

**Change:** Two prompt additions to openai_backend.py: 
    
    (1) populate primary_features only with features whose absolute SHAP value exceeds 20% of the top feature's value; 
    (2) require `explanation` to reference at least one retrieved source (chunk) by name rather than restating SHAP values.

**Motivating example:** evt_001 (concentrated, Gini=0.74, SHAP [1.42, 0.18, 0.07, 0.05, 0.03]) returned all five features as primary despite mean accounting for 81% of attribution. The explanation restated the input with no reference to the seven retrieved chunks.

**Delta:** Added primary_features_focused check; V1 retroactively scores **0.71**. After the fix, V2: mean composite **0.93**, primary_features_focused **0.86**. Two remaining failures are mid severity events where listing two near equal features is correct.

**Conclusion:** Concentrated events now correctly return one primary feature. Explanation grounding improved qualitatively but is hard to score automatically without fuzzy matching. Next: fix anomaly_type defaulting to sensor_fault for all events.

### Anomaly Type Differentiation and Operator Decision Specificity V3

**Change:** Three prompt rules: 

    (1) Infer anomaly_type from channel prefix (D is sensor_fault, A is attitude_anomaly, diffuse is unknown); 
    (2) populate historical_precedent whenever a NASA Lessons Learned chunk scores ≥ 0.65;
    (3) require operator_decision to name the channel and Gini coefficient.

**Motivating example:** evt_002 (A-9, Gini = 0.42) returned anomaly_type: sensor_fault and operator_decision: "The operator may consider the implications..." identical phrasing to all other events. historical_precedent was null despite NASA LL #6914 scoring 0.781.

**Delta:** V2: anomaly_type diversity 1/7 types, historical_precedent null rate 71%. V3 (8 scored, 2 refusals): diversity 3/8 types, null rate 0%. Mean composite **1.00**.

**Conclusion:** Channel based heuristic eliminated sensor_fault defaults. Historical precedent now populated in every report. operator_decision improved but remains formulaic. Next: inject subsystem context and use real SMAP data.

### Subsystem Context Injection and Real SMAP Event Data V4

**Change:** Added a SUBSYSTEM CONTEXT block to the prompt (channel name, role, anomaly class, labeled window indices) derived from the channel ID prefix. Regenerated all 10 test cases from real SMAP telemetry using perturbation-based attribution across 25 channels.

**Motivating example:** evt_006 (E-1, electrical, contextual) returned sensor_fault in V3. With the subsystem block telling the model this is an electrical channel, V4 correctly returns power_anomaly and cites NASA NPR 8705.4A Section 3.2.

**Delta:** V3: 8 scored, 2 refusals, composite 1.00. V4: **10 scored, 0 refusals**, composite **0.975**. top_feature_correct **0.90** (one near-equal feature miss on E-1). Zero refusals confirms real anomaly windows produce cleaner signals than synthetic ones.

**Conclusion:** Subsystem context eliminated remaining type defaults. Zero refusals on real data vs 20% on synthetic is the most meaningful improvement. The one top_feature_correct miss is defensible: std and max have near equal SHAP values in the E-1 window.

---

## 3. Code Walkthrough

A user selects event evt_004 (channel D-3, data/downlink subsystem, point anomaly) with all three source bodies enabled and clicks Generate Report with the openai backend.

The request hits POST /explain in backend/api/app.py:150. The endpoint first checks the disk cache (backend/cache.py:51): a SHA-256 key over (event_id, sorted source_bodies, backend). On a miss, it loads the event JSON from eval/test_cases/event_004.json and builds a retrieval query string that includes the channel prefix, subsystem type, and anomaly class (app.py:170). The Retriever (backend/rag/retriever.py:69) embeds the query with text-embedding-3-small, queries the local ChromaDB collection at backend/chroma_db/, and returns the top 4 regulatory chunks and top 3 historical chunks ranked by cosine similarity.

The enriched event and retrieved chunks are passed to OpenAIBackend.generate() (backend/backends/openai_backend.py:184). _build_initial_messages() at line 105 assembles the prompt: SHAP attribution values sorted by magnitude, a SUBSYSTEM CONTEXT block derived from the D prefix (Data Handling/Downlink), the full event metadata, and the retrieved chunks formatted with source, section, and relevance score. The 11 rule system prompt at line 40 enforces observational language, primary feature selection, citation grounding, and subsystem aware anomaly classification.

The response is parsed and validated by OutputValidator.validate() (backend/validator/output_validator.py). If the prescriptive verb check or schema check fails, the backend appends the error and retries once like in Project 4. On success, app.py:251 enriches each provenance entry with the full chunk text for UI display, writes the result to .report_cache/, and returns ExplainResponse(report = ..., cached = False).

**Design decision:** the LLMBackend ABC (backend/backends/base.py) was chosen over a single function so the mock and OpenAI backends are interchangeable at the endpoint level. The eval harness and the /explain endpoint both call backend.generate(event, retrieved_context) without knowing which backend is active. The rejected alternative was a single generate() function with an if backend == "openai" branch; that would have made the mock harder to test in isolation and would have required touching the endpoint code to add a new backend.

---

## 4. AI Disclosure & Safety

Kiro was used for Pydantic models, FastAPI endpoints, ChromaDB setup, React components, eval harness structure, and the OutputValidator regex. The REPORT.md iterations, system prompt rules, and the decisions on what to measure and change were mine.

Three specific failures worth noting. 

    (1) Kiro wrote eval/run.py passing an empty retrieved_context dict to the OpenAI backend, the eval would have run with no RAG context, making V1 meaningless. I caught this by reading the output carefully; then fixed by adding the normalize_event() function and wiring the retriever into the eval loop. 
    (2) When scaffolding the frontend, Kiro used Python f-string syntax (ch_{channel_index:02d}) inside a JSX expression, causing a TypeScript compile error. Fixed it by replacing with String(channel_index).padStart(2, '0'). 
    (3) Kiro generated corpus.json with the text parameter as null on the first attempt due to a tool payload size limit so the file was empty. Recovered by writing the corpus via a Python builder script run through PowerShell.

Another thing, I found out that Claude Pro has CLI support so I tried it out. I used it for grammar check at the end, and software architecture audit before I wasted time writing junk code. So the report will sound a little robotic but that is because I had it edit my REPORT.md and make my text more legible. It also helped me with debugging/testing when I got stuck (no more spending hours on bugs yay), and had it make the README.md.

**Safety risk:** the primary risk specific to this app is an operator acting on a hallucinated regulatory citation. A report that invents an EU AI Act article number or misattributes a NASA NPR requirement could lead an engineer to make a spacecraft decision based on a non-existent rule. The mitigation is two layered: the system prompt rule 1 explicitly prohibits inventing citations, and the OutputValidator checks that every provenance entry in the report corresponds to a source actually present in the retrieved context. Reports that fail this check are retried once and then returned as degraded_mode = validation_failed rather than served to the operator. The accepted limit is that the validator checks citation presence, not verbatim accuracy. A future improvement would use RapidFuzz fuzzy matching against the retrieved chunk text to catch paraphrased hallucinations.
