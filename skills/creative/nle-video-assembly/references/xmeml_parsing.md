# xmeml (Final Cut Pro XML) parsing

`.prproj` (Premiere) is gzip binary → ask the user to export
`Fichier > Exporter > Final Cut Pro XML`. The result is xmeml v4:

```xml
<xmeml version="4">
  <sequence>
    <rate><timebase>60</timebase><ntsc>FALSE</ntsc></rate>
    <media>
      <video>
        <track type="Video">
          <clipitem id="clipitem-1">
            <name>caentravelling.mp4</name>
            <duration>9292</duration>          <!-- frames -->
            <rate><timebase>60</timebase></rate>
            <start>0</start>                   <!-- timeline frame -->
            <end>9292</end>
            <in>155945</in>                    <!-- source in frame -->
            <out>165237</out>                  <!-- source out frame -->
            <file>
              <name>caentravelling.mp4</name>
              <pathurl>file://localhost/C:/Users/searc/Desktop/4k/caentrav/caentravelling.mp4</pathurl>
            </file>
          </clipitem>
        </track>
      </video>
    </media>
  </sequence>
</xmeml>
```

## Python skeleton (from the worked session)
```python
import xml.etree.ElementTree as ET, os, urllib.parse

def parse(xml_path, source_folder):
    root = ET.parse(xml_path).getroot()
    seq = root.find('.//sequence')
    tb = int(seq.find('.//rate/timebase').text)   # 60
    track = seq.find('.//track[@type="Video"]')
    clips = []
    for ci in track.findall('.//clipitem'):
        name = ci.find('name').text
        in_f  = int(ci.find('in').text)
        out_f = int(ci.find('out').text)
        start = int(ci.find('start').text)
        pathurl = ci.find('.//file/pathurl')
        if pathurl is not None:
            p = urllib.parse.unquote(pathurl.text)
            p = p.replace('file://localhost/', '').replace('file:///', '')
        else:                          # fall back: match name in folder
            p = next((os.path.join(source_folder, f)
                      for f in os.listdir(source_folder)
                      if f.startswith(name)), None)
        clips.append({
            'name': name, 'source_path': p,
            'in_s': in_f / tb, 'out_s': out_f / tb,
            'start_s': start / tb,
        })
    return sorted(clips, key=lambda c: c['start_s'])

# Worked result (caentravelling_4K60_stable.xml):
# 1 clip, source caentravelling.mp4, in 2599.083s, out 2753.95s
# => cut = 154.867s, 50fps source scaled to 1080p.
```

Notes:
- `in`/`out` are SOURCE frame numbers → the cut inside the master file.
- Sort clips by `start` (timeline), not by document order.
- Frames→seconds = value / timebase.
