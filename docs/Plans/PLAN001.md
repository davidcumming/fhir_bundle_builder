## 1. Repo assessment

- The repo currently contains only project guidance docs in [docs/architecture-and-system-requirements.md](/Users/davidcumming/coding_projects/fhir_bundle_builder/docs/architecture-and-system-requirements.md), [docs/microsoft-agent-framework-best-practices.md](/Users/davidcumming/coding_projects/fhir_bundle_builder/docs/microsoft-agent-framework-best-practices.md), [docs/psca-workflow-development-guidance.md](/Users/davidcumming/coding_projects/fhir_bundle_builder/docs/psca-workflow-development-guidance.md), and [docs/development-plan.md](/Users/davidcumming/coding_projects/fhir_bundle_builder/docs/development-plan.md). Those docs are aligned on a small, sequential, workflow-first slice.
- The PS-CA source package is already present under [fhir/ca.infoway.io.psca-2.1.1-dft/package.json](/Users/davidcumming/coding_projects/fhir_bundle_builder/fhir/ca.infoway.io.psca-2.1.1-dft/package.json) with package id `ca.infoway.io.psca`, version `2.1.1-DFT`, FHIR `4.0.1`, plus [fhir/ca.infoway.io.psca-2.1.1-dft/.index.json](/Users/davidcumming/coding_projects/fhir_bundle_builder/fhir/ca.infoway.io.psca-2.1.1-dft/.index.json), bundle/composition profiles, and example bundles such as [fhir/ca.infoway.io.psca-2.1.1-dft/examples/Bundle1Example.json](/Users/davidcumming/coding_projects/fhir_bundle_builder/fhir/ca.infoway.io.psca-2.1.1-dft/examples/Bundle1Example.json).
- There is no application code yet: no `pyproject.toml`, no Python package, no tests, no workflow entity folder for Dev UI discovery, no run script, and no environment/config documentation beyond a minimal README.
- The existing `.venv` is Python 3.10.2 and currently only has `pip` and `setuptools`, so the first slice must establish package/dependency setup from scratch.
- Real constraints for this slice: keep everything deterministic, do not start the normalization pipeline, do not encode real PS-CA rules in prompts, and make every stage visibly inspectable in Dev UI.

## 2. Proposed slice scope

- Implement the smallest Python-based Microsoft Agent Framework workflow that proves the PS-CA workflow shape in Dev UI, because the repo already has a Python venv and no .NET setup.
- Use directory-based Dev UI discovery, not a custom bootstrap app, because it is the simplest path to visible workflow registration and inspection in this repo shape per [DevUI Overview](https://learn.microsoft.com/en-us/agent-framework/devui/) and [Directory Discovery](https://learn.microsoft.com/en-us/agent-framework/devui/directory-discovery).
- Keep the slice bounded to typed input, sequential wiring, placeholder executors, structured artifacts, smoke tests, and run instructions.
- Explicitly do not implement real bundle generation, real validation, real profile retrieval, or real PS-CA asset normalization in this slice.

## 3. Proposed workflow skeleton

- Workflow shape: `request_normalization -> specification_asset_retrieval -> bundle_schematic -> build_plan -> resource_construction -> bundle_finalization -> validation -> repair_decision`.
- Top-level input model: a nested typed request object with `specification`, `patient_profile`, `provider_profile`, `request`, and `workflow_options`. Default the specification to `ca.infoway.io.psca` / `2.1.1-DFT`; keep patient/provider references and request text explicit.
- Stage artifacts:
  - `NormalizedBuildRequest`
  - `SpecificationAssetContextStub`
  - `BundleSchematicStub`
  - `BuildPlanStub`
  - `ResourceConstructionStageResult`
  - `CandidateBundleStub`
  - `ValidationReportStub`
  - `RepairDecisionStub`
- Each artifact should include common inspectability fields such as `stage_id`, `status`, `summary`, `placeholder_note`, and `source_refs`, plus stage-specific structured fields.
- The spec retrieval executor should read only existing repo artifacts deterministically: package metadata, `.index.json`, the bundle/composition profile files, and one example bundle inventory. It should return a stub context that clearly says normalization is not implemented yet.
- The resource construction stage should stay as one executor for this slice, but return a structured list of placeholder per-resource build results so the ordered-build concept is visible without adding subworkflows yet.
- The terminal executor should yield a final `WorkflowSkeletonRunResult` that nests all stage artifacts so the full run is inspectable from the Dev UI output panel as well as per-executor events.
- No LLM calls, no prompts, and no credentials should be required for this slice; the workflow should be fully deterministic and runnable offline once the framework packages are installed.

## 4. File-level change plan

- `pyproject.toml`
  - Define the Python project, `src/` layout, and minimal dependencies: `agent-framework-core`, `agent-framework-devui`, `pydantic`, `typing_extensions`, plus test deps such as `pytest` and `pytest-asyncio`.
- `src/fhir_bundle_builder/__init__.py`
  - Package marker.
- `src/fhir_bundle_builder/workflows/psca_bundle_builder_workflow/models.py`
  - All input, artifact, and final-output models for the slice.
- `src/fhir_bundle_builder/workflows/psca_bundle_builder_workflow/executors.py`
  - The placeholder executors and the small deterministic PS-CA package inspection helpers they need.
- `src/fhir_bundle_builder/workflows/psca_bundle_builder_workflow/workflow.py`
  - Build and name the sequential workflow using `WorkflowBuilder` per [Workflow Builder & Execution](https://learn.microsoft.com/en-us/agent-framework/workflows/workflows).
- `entities/psca_bundle_builder_workflow/__init__.py`
  - Export `workflow = ...` so Dev UI can discover it directly.
- `tests/test_psca_bundle_builder_workflow.py`
  - Smoke test that runs the workflow directly and asserts stage order and structured outputs.
- `README.md`
  - Replace the placeholder README with setup, install, launch, and “what you should see in Dev UI” instructions.

## 5. Step-by-step implementation plan

1. Add project packaging and dependency metadata so the repo can be installed editable and imported cleanly from Dev UI.
2. Create the typed top-level input model and the stage artifact models first, because Dev UI input generation and executor boundaries depend on those contracts.
3. Implement deterministic placeholder executors in stage order, with the spec retrieval stage reading the actual PS-CA package metadata and example inventory from the repo.
4. Wire the workflow sequentially and export it through `entities/psca_bundle_builder_workflow/__init__.py` for directory-based discovery.
5. Add a direct workflow smoke test that executes the graph without Dev UI and verifies the final output contains all expected stage artifacts.
6. Update `README.md` with concrete commands:
   - activate `.venv`
   - `pip install -e .[dev]`
   - `devui ./entities --reload --port 8080`
7. Validate locally by confirming the workflow is discovered by Dev UI, the form reflects the structured input schema, and the run emits executor outputs in the expected order.

## 6. Definition of Done

- `devui ./entities --reload` discovers one workflow named for the PS-CA bundle builder skeleton.
- Dev UI renders a structured form from the first executor’s input type rather than a single free-text box.
- A run completes end to end through all placeholder stages with no external model credentials required.
- The Dev UI event stream shows executor completion entries for all major stages in the documented order.
- Each stage output is structured and human-inspectable, not opaque prose.
- The final workflow output contains a complete nested run summary with all stage artifacts.
- The repo has a repeatable install/run path and a smoke test for the skeleton workflow.

## 7. Risks / notes

- The Microsoft Agent Framework Python packages are still prerelease; API details may shift slightly at implementation time. The plan assumes the current documented package split and workflow builder API remain valid.
- Dev UI input-schema behavior is documented at a high level but not deeply specified; using Pydantic models is a design choice to maximize typed schema introspection. That is an implementation inference, not an explicit repo fact.
- This slice should read raw PS-CA package files only to produce inspectable stubs. If it starts deriving real rules or real normalized assets, it has crossed into Phase 3 scope.
- Keep the placeholder schematic/build-plan content intentionally modest. Reusing a few example-derived resource types is fine; encoding real section logic from the guide is not.

## 8. Targeted `docs/development-plan.md` updates after implementation

- In [docs/development-plan.md](/Users/davidcumming/coding_projects/fhir_bundle_builder/docs/development-plan.md) Section 8, change `Current Focus` from planning/workflow-foundation setup to the next bounded slice: PS-CA asset retrieval and initial normalized asset contract.
- In Section 9, replace the current `Next Planned Slice` with a narrower Phase 3 entry such as “Implement initial PS-CA asset retrieval boundary and first normalized asset context stub from the existing package files.”
- In Section 10, mark `Phase 2: Minimal Workflow Skeleton in Dev UI` as `Completed`.
- In Section 10, mark `Phase 1: Foundation and Project Guidance` as `Completed` if you consider the guidance baseline now proven sufficient by a working slice.
- In Section 16, replace the immediate next objective so it no longer points to “implement the first visible workflow skeleton” and instead points to proving the first workflow-usable PS-CA asset retrieval path.
- In Section 13, add one concise new risk only if it was observed during implementation: dependency on prerelease Agent Framework package behavior for Dev UI discovery/schema rendering.
