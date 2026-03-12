# PS-CA Source Inventory

This document records the initial PS-CA source inputs we plan to stage for later manifest extraction work. The authoritative package is available locally under [fhir/ca.infoway.io.psca-2.1.1-dft](/C:/Users/david/source/repos/fhir_bundle_builder/fhir/ca.infoway.io.psca-2.1.1-dft).

## Initial Inventory

Profile and metadata files:
- [fhir/ca.infoway.io.psca-2.1.1-dft/structuredefinition-profile-bundle-ca-ps.json](/C:/Users/david/source/repos/fhir_bundle_builder/fhir/ca.infoway.io.psca-2.1.1-dft/structuredefinition-profile-bundle-ca-ps.json)
- [fhir/ca.infoway.io.psca-2.1.1-dft/structuredefinition-profile-composition-ca-ps.json](/C:/Users/david/source/repos/fhir_bundle_builder/fhir/ca.infoway.io.psca-2.1.1-dft/structuredefinition-profile-composition-ca-ps.json)
- [fhir/ca.infoway.io.psca-2.1.1-dft/structuredefinition-profile-patient-ca-ps.json](/C:/Users/david/source/repos/fhir_bundle_builder/fhir/ca.infoway.io.psca-2.1.1-dft/structuredefinition-profile-patient-ca-ps.json)
- [fhir/ca.infoway.io.psca-2.1.1-dft/structuredefinition-profile-condition-ca-ps.json](/C:/Users/david/source/repos/fhir_bundle_builder/fhir/ca.infoway.io.psca-2.1.1-dft/structuredefinition-profile-condition-ca-ps.json)
- [fhir/ca.infoway.io.psca-2.1.1-dft/structuredefinition-profile-allergyintolerance-ca-ps.json](/C:/Users/david/source/repos/fhir_bundle_builder/fhir/ca.infoway.io.psca-2.1.1-dft/structuredefinition-profile-allergyintolerance-ca-ps.json)
- [fhir/ca.infoway.io.psca-2.1.1-dft/structuredefinition-profile-medicationrequest-ca-ps.json](/C:/Users/david/source/repos/fhir_bundle_builder/fhir/ca.infoway.io.psca-2.1.1-dft/structuredefinition-profile-medicationrequest-ca-ps.json)
- [fhir/ca.infoway.io.psca-2.1.1-dft/structuredefinition-profile-medicationstatement-ca-ps.json](/C:/Users/david/source/repos/fhir_bundle_builder/fhir/ca.infoway.io.psca-2.1.1-dft/structuredefinition-profile-medicationstatement-ca-ps.json)
- [fhir/ca.infoway.io.psca-2.1.1-dft/structuredefinition-profile-procedure-ca-ps.json](/C:/Users/david/source/repos/fhir_bundle_builder/fhir/ca.infoway.io.psca-2.1.1-dft/structuredefinition-profile-procedure-ca-ps.json)
- [fhir/ca.infoway.io.psca-2.1.1-dft/package.json](/C:/Users/david/source/repos/fhir_bundle_builder/fhir/ca.infoway.io.psca-2.1.1-dft/package.json)

Example bundles:
- [fhir/ca.infoway.io.psca-2.1.1-dft/examples/Bundle1Example.json](/C:/Users/david/source/repos/fhir_bundle_builder/fhir/ca.infoway.io.psca-2.1.1-dft/examples/Bundle1Example.json)
- [fhir/ca.infoway.io.psca-2.1.1-dft/examples/Bundle-FulsomeClinicalScenario1.json](/C:/Users/david/source/repos/fhir_bundle_builder/fhir/ca.infoway.io.psca-2.1.1-dft/examples/Bundle-FulsomeClinicalScenario1.json)

## Why These Files Matter

- Bundle and Composition profiles are the starting point for bundle-level assembly rules, section structure, and document constraints.
- Core resource profiles define the resource-level shape we need to account for when planning manifest extraction and later build steps.
- Example bundles give us concrete PS-CA instances for grounding and cross-checking future extraction work against real package examples.
- `package.json` gives us package identity and metadata that will matter once we start manifest extraction and package-aware processing.

## Current Scope

This step is limited to staging and documentation only. No parsing, transformation, or manifest extraction has been done yet.
