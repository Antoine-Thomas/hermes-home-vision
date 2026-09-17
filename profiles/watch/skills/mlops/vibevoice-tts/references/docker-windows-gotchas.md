# Docker-on-Windows gotchas (vibevoice-dev)

## pkill -f self-kill (exit 143)
`bash vibevoice.sh stop` does `docker exec ... bash -c "pkill -f gradio_demo"`. When you run that yourself as
`docker exec ... bash -c 'pkill -f gradio_demo ...'`, pkill's `-f` matches the invoking shell's OWN command line
(which contains the literal string "gradio_demo") and SIGTERMs it → empty output, exit 143. Harmless but confusing.
Safe stop: check first whether a demo is even running — a freshly `docker start`ed container has none:
```
docker exec vibevoice-dev bash -c 'ps aux | grep -i python | grep -v grep'
```
If a demo IS running, kill by PID (don't put the match string in your own bash -c command).

## Container Exited(255) after Docker Desktop restart
After the host reboots / Docker Desktop restarts, `vibevoice-dev` shows `Exited (255)`. `docker start vibevoice-dev`
revives it, BUT it can exit again (255) once within the first ~30s while the WSL2 backend finishes initializing.
Just `docker start` again and poll `docker ps` — the second start sticks. Verify the GPU before the big work:
```
docker exec vibevoice-dev nvidia-smi --query-gpu=name,memory.free --format=csv,noheader
```
(8 GB card with ~2.5-2.8 GB already used by the Windows host → ~5.3-5.5 GB free; the 1.5B model needs ~5.4 GB, tight but it fits.)

## MSYS path conversion
In git-bash, prefix `docker exec` with `MSYS_NO_PATHCONV=1` whenever a container path starts with `/`
(e.g. `/workspace/...`), or it gets rewritten to a Git path and the command errors.
