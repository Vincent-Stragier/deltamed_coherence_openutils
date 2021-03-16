# Deltamed Coherence openutils
This repository contains some tools created to manipulate Deltamed Coherence .eeg data in batch. First, an anonymisation tool has been created, then a wrapper for the Deltamed coh3toEDF converter (coh3 is the version of the `.eeg` format used).

## Jobs status
In order to improve the code quality, a linter, some unit tests and a security test are run over the codebase using some workflows (GitHub Actions). This aim to insure that the code is always working as intended.

### Status of the workflows on the main branch
![Lastest released development build](https://github.com/2010019970909/deltamed_coherence_openutils/actions/workflows/release_lastest.yml/badge.svg?branch=main)
![Linting](https://github.com/2010019970909/deltamed_coherence_openutils/actions/workflows/linter.yml/badge.svg?branch=main)
![Unit test](https://github.com/2010019970909/deltamed_coherence_openutils/actions/workflows/code_coverage.yml/badge.svg?branch=main)
![CodeQl](https://github.com/2010019970909/deltamed_coherence_openutils/actions/workflows/codeql-analysis.yml/badge.svg?branch=main)

### Status of the workflows on the dev branch (pull request to main)
![Linting](https://github.com/2010019970909/deltamed_coherence_openutils/actions/workflows/linter.yml/badge.svg?branch=dev)
![Unit test](https://github.com/2010019970909/deltamed_coherence_openutils/actions/workflows/code_coverage.yml/badge.svg?branch=dev)
![CodeQl](https://github.com/2010019970909/deltamed_coherence_openutils/actions/workflows/codeql-analysis.yml/badge.svg?branch=dev)
