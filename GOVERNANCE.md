# Governance

The repository owner maintains releases and reviews changes. Contributions are licensed Apache-2.0.
Business ontology owners review semantic changes; code maintainers review implementation and tests.
Certification records reviewer identity supplied by the trusted maintainer and the proposal digest.
It is a review label, not a digital signature or guarantee of source-data accuracy.

Use semantic versions for ontology documents and package releases independently. Breaking changes
to identifiers, metric meanings, field types, or access scopes require a new major ontology version
and migration notes. Keep old definitions available in Git; each running service exposes its active
version. Never silently reuse an identifier for a different business meaning.

Enable protected branches and required CI checks in GitHub for shared teams. The package does not
automatically change account-level repository protections.
