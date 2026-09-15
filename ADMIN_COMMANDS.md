# Admin commands

## Refresh Champions learnsets

From the repository root, activate the virtual environment:

```sh
source .venv/bin/activate
```

Download and validate the latest Showdown Champions learnsets, then replace the local file:

```sh
python -m damage_agent.champions_learnsets
```

This updates `data/champions_learnsets.json` on disk. It does not populate a memory cache.
If downloading or validation fails, the existing file is preserved.

Review and publish the updated data:

```sh
git diff -- data/champions_learnsets.json
git add data/champions_learnsets.json
git commit -m "Update Champions learnsets"
git push
```

Render uses the updated file on its next deployment. Refresh the Team Builder page to load updated move choices locally.
