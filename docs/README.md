# Documentation

The [README](../README.md) gives the quick start and the rules of the layout.
Start the [tutorial](tutorial/README.md) to learn the design step by step.

## How-to guides

- [Run the application in a container](how-to/run-in-a-container.md)
- [Use the SQLite backend](how-to/use-the-sqlite-backend.md)
- [Add an adapter for an external API](how-to/add-an-external-api.md)
- [Report a bustan issue, or send a fix](how-to/report-a-bustan-issue.md)
- [Cut a release](how-to/cut-a-release.md)

## Explanation

- [bustan or FastAPI](explanation/bustan-or-fastapi.md): the rules that
  bustan enforces, the cases for FastAPI, and a section for the `AGENTS.md`
  of a project.

## Reference

- [Configuration](reference/configuration.md): each environment variable.
- [Tooling](reference/tooling.md): the commands, the hooks, CI and the release workflow.
- [API](../openapi.yaml): the OpenAPI document, made from the code.
- [Agent skill](../.agents/skills/bustan-dev/SKILL.md): the rules, recipes and
  scripts for bustan projects.

## Tutorial

[The tutorial](tutorial/README.md) goes from the first request to the
trade-offs of the design, in ten chapters: run it, modules and injection, one
request, the domain, ports and storage, identity and security, events and
jobs, testing, operations, and a capstone feature. The reasons behind each
part of the design are in the chapters.
