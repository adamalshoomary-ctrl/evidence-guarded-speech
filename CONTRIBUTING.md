# Getting help, and what happens to pull requests

Open an issue. Include the command you ran, the whole error, your operating
system and your Python version. If a run produced an `output/master.json`, its
`provenance` block answers most questions on its own.

Never paste a `.env` file or attach an audio recording. `SECURITY.md` explains
why.

This is a research artifact by one author rather than a maintained library.
Bug reports and questions are welcome. Feature work probably is not, and the
author may decline a pull request without a long explanation. If you want the
code to do something else, the licence is GPL 3.0 or later and forking is a
reasonable answer.

Before opening an issue about a command that failed, check `README.md` for the
credentials that command needs, and check that `ffmpeg -version` works.
