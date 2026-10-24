# Publishing checklist

The repository has been public since 2026-10-24, with Jadon's approval; the
[validation log](validation.md#repository-made-public-2026-10-24) records the
checks before the change. Before anything drawn from it, such as a portfolio
case study or a guide, is published, these checks pass and Jadon approves the
exact content and destination. Passing the checks alone authorizes nothing.

The repository is the technical source of truth. Personal planning, questions
and reflections belong in Obsidian. Neither the app nor its documentation is a
finished portfolio case study or a homelab guide.

## Portfolio

- [ ] Describe only implemented behavior, and distinguish agent work from
  Jadon's reviewed contribution and understanding.
- [ ] Link meaningful changes, test results and sanitized screenshots from
  real runs; label mockups and planned behavior.
- [ ] Explain the problem, one or two design choices and the verified
  limitations.
- [ ] Remove private paths, addresses, host aliases, account details and
  secrets.
- [x] Choose a license: MIT, decided on 2026-10-20.
- [ ] Jadon approves the exact content and destination.

## Homelab guide or helper

- [ ] Base instructions on implemented features and approved repeatable tests.
- [ ] State prerequisites, tested operating systems and the native SSH
  boundary.
- [ ] Use fictional examples and document expected results, failure handling
  and safe recovery without weakening authentication or host-key checks.
- [ ] Jadon reviews the steps and privacy before anything is published.
  Building a guide site is a separate task.

## Evidence worth keeping

| Keep | Where |
| --- | --- |
| Dated manual checks | [The validation log](validation.md) and [its archive](archive/validation-tasks-1-18.md) |
| Changes, test results and CI runs | Pull requests on GitHub |
| Design decisions | [Architecture](architecture.md) |
| Usability observations Jadon approved, and questions he wants to explore | Obsidian until sanitized |

Never invent reflections, test results or claims of experience. Beyond the
public repository, the project has no site, release automation or other
publication.
