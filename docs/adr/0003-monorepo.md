# One repository for all components

The api, scheduler, worker and web frontend live in one repository: one README tells the whole story, and a change that spans the api and the frontend lands in one pull request. CI runs only the jobs whose folders changed (path filters), so the components still build and deploy independently.

## Considered options

- **Separate repositories** (`uptime-watch-api`, `uptime-watch-web`): rejected. It means separate pipelines and versioning that must be coordinated, which is more overhead than a one-person project gains from it.
