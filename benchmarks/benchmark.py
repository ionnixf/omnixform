#!/usr/bin/env python3
"""
Omnixform Exploratory Benchmark Suite

Local smoke/comparison tool. Results are not release evidence unless the
environment, inputs, tool versions, and equivalent options are recorded.

Compares Omnixform against common alternatives:
- ImageMagick (magick/convert)
- FFmpeg (direct)
- Pandoc (direct)
- LibreOffice (soffice headless)

Run: python benchmarks/benchmark.py
"""

from __future__ import annotations

import json
import shutil
import subprocess
import sys
import tempfile
import time
from pathlib import Path
from typing import Any

# Add src to path for local imports
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from omnixform.adapters.images import ImageAdapter
from omnixform.adapters.libreoffice import LibreOfficeAdapter
from omnixform.adapters.multimedia import MultimediaAdapter
from omnixform.adapters.pandoc import PandocAdapter
from omnixform.adapters.structured_data import StructuredDataAdapter


class BenchmarkResult:
    def __init__(self, name: str):
        self.name = name
        self.iterations: list[dict[str, Any]] = []

    def add(self, tool: str, duration_ms: float, success: bool, output_size: int = 0, error: str = ""):
        self.iterations.append(
            {
                "tool": tool,
                "duration_ms": round(duration_ms, 2),
                "success": success,
                "output_size_bytes": output_size,
                "error": error,
            }
        )

    def summary(self) -> dict[str, Any]:
        by_tool: dict[str, list[float]] = {}
        for it in self.iterations:
            if it["success"]:
                by_tool.setdefault(it["tool"], []).append(it["duration_ms"])

        result = {"name": self.name}
        for tool, times in by_tool.items():
            result[tool] = {
                "mean_ms": round(sum(times) / len(times), 2),
                "min_ms": round(min(times), 2),
                "max_ms": round(max(times), 2),
                "runs": len(times),
            }
        return result


def run_cmd(cmd: list[str], timeout: int = 60) -> tuple[float, int, str, str]:
    """Run command and return (duration_ms, returncode, stdout, stderr)."""
    start = time.perf_counter()
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
        duration = (time.perf_counter() - start) * 1000
        return duration, result.returncode, result.stdout, result.stderr
    except subprocess.TimeoutExpired:
        duration = (time.perf_counter() - start) * 1000
        return duration, -1, "", "TIMEOUT"
    except FileNotFoundError:
        return 0, -1, "", "NOT_FOUND"


def check_tool(name: str) -> bool:
    """Check if a command-line tool is available."""
    return shutil.which(name) is not None


def create_test_image(path: Path, size: tuple[int, int] = (1920, 1080), mode: str = "RGBA"):
    """Create a test image using Pillow."""
    from PIL import Image

    img = Image.new(mode, size, color=(100, 150, 200, 255))
    # Add some detail
    from PIL import ImageDraw

    draw = ImageDraw.Draw(img)
    for i in range(0, size[0], 50):
        draw.line([(i, 0), (i, size[1])], fill=(200, 100, 50, 128), width=1)
    for i in range(0, size[1], 50):
        draw.line([(0, i), (size[0], i)], fill=(50, 200, 100, 128), width=1)
    img.save(path)


def create_test_video(path: Path, duration: float = 2.0):
    """Create a test video using FFmpeg."""
    if not check_tool("ffmpeg"):
        return False
    cmd = [
        "ffmpeg",
        "-y",
        "-f",
        "lavfi",
        "-i",
        f"testsrc=duration={duration}:size=1280x720:rate=30",
        "-c:v",
        "libx264",
        "-preset",
        "fast",
        "-crf",
        "23",
        str(path),
    ]
    result = subprocess.run(cmd, capture_output=True, text=True)
    return result.returncode == 0


def create_test_audio(path: Path, duration: float = 2.0):
    """Create a test audio file."""
    if not check_tool("ffmpeg"):
        return False
    cmd = [
        "ffmpeg",
        "-y",
        "-f",
        "lavfi",
        "-i",
        f"sine=frequency=440:duration={duration}",
        "-c:a",
        "pcm_s16le",
        str(path),
    ]
    result = subprocess.run(cmd, capture_output=True, text=True)
    return result.returncode == 0


def create_test_docx(path: Path):
    """Create a test DOCX file."""
    if not check_tool("libreoffice") and not check_tool("soffice"):
        # Create a simple one with python-docx if available
        try:
            from docx import Document

            doc = Document()
            doc.add_heading("Test Document", 0)
            for i in range(10):
                doc.add_paragraph(f"This is paragraph {i} with some text content.")
                doc.add_paragraph(f"Another line {i} with more text.")
            doc.save(path)
            return True
        except ImportError:
            pass
    return False


def create_test_csv(path: Path, rows: int = 1000):
    """Create a test CSV file."""
    import csv

    with open(path, "w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["id", "name", "value", "category", "timestamp"])
        for i in range(rows):
            writer.writerow([i, f"item_{i}", i * 1.5, f"cat_{i % 10}", f"2024-01-{(i % 28) + 1:02d}"])


def create_test_json(path: Path, items: int = 1000):
    """Create a test JSON file."""
    data = [
        {"id": i, "name": f"item_{i}", "value": i * 1.5, "tags": ["a", "b"][: i % 2 + 1]}
        for i in range(items)
    ]
    with open(path, "w") as f:
        json.dump(data, f)


def benchmark_image_conversion(temp_dir: Path, result: BenchmarkResult, iterations: int = 5):
    """Benchmark PNG -> WebP conversion."""
    input_path = temp_dir / "test.png"
    create_test_image(input_path)

    # Omnixform (Pillow)
    adapter = ImageAdapter()
    if not adapter.is_available():
        print("  ⚠ Pillow not available")
    else:
        for i in range(iterations):
            output = temp_dir / f"ff_webp_{i}.webp"
            start = time.perf_counter()
            try:
                adapter.convert(str(input_path), "webp", output_path=str(output), options={"quality": 90})
                duration = (time.perf_counter() - start) * 1000
                result.add("omnixform-pillow", duration, True, output.stat().st_size)
            except Exception as e:
                result.add("omnixform-pillow", 0, False, error=str(e))

    # ImageMagick
    if check_tool("magick"):
        for i in range(iterations):
            output = temp_dir / f"im_webp_{i}.webp"
            duration, code, _, stderr = run_cmd(["magick", str(input_path), "-quality", "90", str(output)])
            if code == 0:
                result.add("imagemagick", duration, True, output.stat().st_size)
            else:
                result.add("imagemagick", duration, False, error=stderr[:100])
    elif check_tool("convert"):  # legacy ImageMagick 6
        for i in range(iterations):
            output = temp_dir / f"im_webp_{i}.webp"
            duration, code, _, stderr = run_cmd(["convert", str(input_path), "-quality", "90", str(output)])
            if code == 0:
                result.add("imagemagick", duration, True, output.stat().st_size)
            else:
                result.add("imagemagick", duration, False, error=stderr[:100])


def benchmark_video_conversion(temp_dir: Path, result: BenchmarkResult, iterations: int = 3):
    """Benchmark MOV -> MP4 conversion."""
    input_path = temp_dir / "test.mov"
    if not create_test_video(input_path):
        print("  ⚠ Could not create test video (ffmpeg not available)")
        return

    # Omnixform (FFmpeg)
    adapter = MultimediaAdapter()
    if adapter.is_available():
        for i in range(iterations):
            output = temp_dir / f"ff_mp4_{i}.mp4"
            start = time.perf_counter()
            try:
                adapter.convert(str(input_path), "mp4", output_path=str(output))
                duration = (time.perf_counter() - start) * 1000
                result.add("omnixform-ffmpeg", duration, True, output.stat().st_size)
            except Exception as e:
                result.add("omnixform-ffmpeg", 0, False, error=str(e))

    # Direct FFmpeg
    if check_tool("ffmpeg"):
        for i in range(iterations):
            output = temp_dir / f"ffmpeg_mp4_{i}.mp4"
            duration, code, _, stderr = run_cmd(
                [
                    "ffmpeg",
                    "-y",
                    "-i",
                    str(input_path),
                    "-c:v",
                    "libx264",
                    "-preset",
                    "medium",
                    "-crf",
                    "23",
                    "-c:a",
                    "aac",
                    "-b:a",
                    "128k",
                    str(output),
                ],
                timeout=120,
            )
            if code == 0:
                result.add("ffmpeg-direct", duration, True, output.stat().st_size)
            else:
                result.add("ffmpeg-direct", duration, False, error=stderr[:100])


def benchmark_audio_conversion(temp_dir: Path, result: BenchmarkResult, iterations: int = 5):
    """Benchmark WAV -> MP3 conversion."""
    input_path = temp_dir / "test.wav"
    if not create_test_audio(input_path):
        print("  ⚠ Could not create test audio")
        return

    # Omnixform
    adapter = MultimediaAdapter()
    if adapter.is_available():
        for i in range(iterations):
            output = temp_dir / f"ff_mp3_{i}.mp3"
            start = time.perf_counter()
            try:
                adapter.convert(
                    str(input_path), "mp3", output_path=str(output), options={"audio_bitrate": "192k"}
                )
                duration = (time.perf_counter() - start) * 1000
                result.add("omnixform-ffmpeg", duration, True, output.stat().st_size)
            except Exception as e:
                result.add("omnixform-ffmpeg", 0, False, error=str(e))

    # Direct FFmpeg
    if check_tool("ffmpeg"):
        for i in range(iterations):
            output = temp_dir / f"ffmpeg_mp3_{i}.mp3"
            duration, code, _, stderr = run_cmd(
                ["ffmpeg", "-y", "-i", str(input_path), "-c:a", "libmp3lame", "-b:a", "192k", str(output)]
            )
            if code == 0:
                result.add("ffmpeg-direct", duration, True, output.stat().st_size)
            else:
                result.add("ffmpeg-direct", duration, False, error=stderr[:100])


def benchmark_docx_to_pdf(temp_dir: Path, result: BenchmarkResult, iterations: int = 3):
    """Benchmark DOCX -> PDF conversion."""
    input_path = temp_dir / "test.docx"
    if not create_test_docx(input_path):
        print("  ⚠ Could not create test DOCX")
        return

    # Omnixform (LibreOffice)
    adapter = LibreOfficeAdapter()
    if adapter.is_available():
        for i in range(iterations):
            output = temp_dir / f"ff_pdf_{i}.pdf"
            start = time.perf_counter()
            try:
                adapter.convert(str(input_path), "pdf", output_path=str(output))
                duration = (time.perf_counter() - start) * 1000
                result.add("omnixform-libreoffice", duration, True, output.stat().st_size)
            except Exception as e:
                result.add("omnixform-libreoffice", 0, False, error=str(e))

    # LibreOffice direct
    if check_tool("soffice") or check_tool("libreoffice"):
        lo_cmd = "soffice" if check_tool("soffice") else "libreoffice"
        for i in range(iterations):
            output_dir = temp_dir / f"lo_out_{i}"
            output_dir.mkdir(exist_ok=True)
            duration, code, _, stderr = run_cmd(
                [lo_cmd, "--headless", "--convert-to", "pdf", "--outdir", str(output_dir), str(input_path)],
                timeout=120,
            )
            output_file = output_dir / "test.pdf"
            if code == 0 and output_file.exists():
                result.add("libreoffice-direct", duration, True, output_file.stat().st_size)
            else:
                result.add("libreoffice-direct", duration, False, error=stderr[:100])

    # Pandoc (if available)
    adapter = PandocAdapter()
    if adapter.is_available():
        for i in range(iterations):
            output = temp_dir / f"pandoc_pdf_{i}.pdf"
            start = time.perf_counter()
            try:
                adapter.convert(str(input_path), "pdf", output_path=str(output))
                duration = (time.perf_counter() - start) * 1000
                result.add("omnixform-pandoc", duration, True, output.stat().st_size)
            except Exception as e:
                result.add("omnixform-pandoc", 0, False, error=str(e))


def benchmark_csv_json(temp_dir: Path, result: BenchmarkResult, iterations: int = 10):
    """Benchmark CSV -> JSON conversion."""
    input_path = temp_dir / "test.csv"
    create_test_csv(input_path, rows=5000)

    # Omnixform
    adapter = StructuredDataAdapter()
    for i in range(iterations):
        output = temp_dir / f"ff_json_{i}.json"
        start = time.perf_counter()
        try:
            adapter.convert(str(input_path), "json", output_path=str(output))
            duration = (time.perf_counter() - start) * 1000
            result.add("omnixform-structured", duration, True, output.stat().st_size)
        except Exception as e:
            result.add("omnixform-structured", 0, False, error=str(e))

    # Python json module direct (baseline)
    for i in range(iterations):
        output = temp_dir / f"py_json_{i}.json"
        start = time.perf_counter()
        try:
            import csv as csv_module

            with open(input_path) as f:
                reader = csv_module.DictReader(f)
                data = list(reader)
            with open(output, "w") as f:
                json.dump(data, f)
            duration = (time.perf_counter() - start) * 1000
            result.add("python-json-direct", duration, True, output.stat().st_size)
        except Exception as e:
            result.add("python-json-direct", 0, False, error=str(e))

    # jq (if available)
    if check_tool("jq"):
        for i in range(iterations):
            output = temp_dir / f"jq_json_{i}.json"
            duration, code, _, stderr = run_cmd(
                [
                    "jq",
                    "-R",
                    "-s",
                    'split("\\n") | map(split(",")) | .[0] as $h | .[1:] | map({($h[i]): .[i]})',
                    str(input_path),
                ],
                timeout=30,
            )
            # jq CSV to JSON is complex, skip for now
            pass


def benchmark_json_yaml(temp_dir: Path, result: BenchmarkResult, iterations: int = 10):
    """Benchmark JSON -> YAML conversion."""
    input_path = temp_dir / "test.json"
    create_test_json(input_path, items=2000)

    adapter = StructuredDataAdapter()
    for i in range(iterations):
        output = temp_dir / f"ff_yaml_{i}.yaml"
        start = time.perf_counter()
        try:
            adapter.convert(str(input_path), "yaml", output_path=str(output))
            duration = (time.perf_counter() - start) * 1000
            result.add("omnixform-structured", duration, True, output.stat().st_size)
        except Exception as e:
            result.add("omnixform-structured", 0, False, error=str(e))

    # Python yaml direct
    for i in range(iterations):
        output = temp_dir / f"py_yaml_{i}.yaml"
        start = time.perf_counter()
        try:
            import yaml

            with open(input_path) as f:
                data = json.load(f)
            with open(output, "w") as f:
                yaml.dump(data, f)
            duration = (time.perf_counter() - start) * 1000
            result.add("python-yaml-direct", duration, True, output.stat().st_size)
        except Exception as e:
            result.add("python-yaml-direct", 0, False, error=str(e))


def run_all_benchmarks(iterations: int = 5) -> list[BenchmarkResult]:
    """Run all benchmarks."""
    results = []

    with tempfile.TemporaryDirectory() as tmp:
        temp_dir = Path(tmp)
        print(f"Working directory: {temp_dir}")

        # Image conversion
        print("\n📸 Benchmarking PNG → WebP...")
        img_result = BenchmarkResult("PNG → WebP (1920x1080)")
        benchmark_image_conversion(temp_dir, img_result, iterations)
        results.append(img_result)

        # Video conversion
        print("\n🎬 Benchmarking MOV → MP4...")
        vid_result = BenchmarkResult("MOV → MP4 (1280x720, 2s)")
        benchmark_video_conversion(temp_dir, vid_result, min(iterations, 3))
        results.append(vid_result)

        # Audio conversion
        print("\n🎵 Benchmarking WAV → MP3...")
        aud_result = BenchmarkResult("WAV → MP3 (2s)")
        benchmark_audio_conversion(temp_dir, aud_result, iterations)
        results.append(aud_result)

        # Document conversion
        print("\n📄 Benchmarking DOCX → PDF...")
        doc_result = BenchmarkResult("DOCX → PDF")
        benchmark_docx_to_pdf(temp_dir, doc_result, min(iterations, 3))
        results.append(doc_result)

        # CSV → JSON
        print("\n📊 Benchmarking CSV → JSON (5000 rows)...")
        csv_result = BenchmarkResult("CSV → JSON (5000 rows)")
        benchmark_csv_json(temp_dir, csv_result, iterations)
        results.append(csv_result)

        # JSON → YAML
        print("\n📋 Benchmarking JSON → YAML (2000 items)...")
        yaml_result = BenchmarkResult("JSON → YAML (2000 items)")
        benchmark_json_yaml(temp_dir, yaml_result, iterations)
        results.append(yaml_result)

    return results


def print_results(results: list[BenchmarkResult]):
    """Print benchmark results in a nice table."""
    print("\n" + "=" * 80)
    print("BENCHMARK RESULTS")
    print("=" * 80)

    for r in results:
        summary = r.summary()
        print(f"\n📊 {summary['name']}")
        print("-" * 60)

        tools = [key for key in summary if key != "name"]
        if not tools:
            print("  No successful runs")
            continue

        # Find fastest
        fastest_tool = min(tools, key=lambda t: summary[t]["mean_ms"])
        fastest_time = summary[fastest_tool]["mean_ms"]

        for tool in tools:
            data = summary[tool]
            marker = " 🏆" if tool == fastest_tool else ""
            speedup = "" if tool == fastest_tool else f" ({data['mean_ms'] / fastest_time:.2f}x slower)"
            timing = f"min: {data['min_ms']:.1f}, max: {data['max_ms']:.1f}, n={data['runs']}"
            print(f"  {tool:25s}  {data['mean_ms']:>8.1f} ms  ({timing}){marker}{speedup}")


def save_results(results: list[BenchmarkResult], output: Path):
    """Save results as JSON."""
    data = [r.summary() for r in results]
    with open(output, "w") as f:
        json.dump(data, f, indent=2)
    print(f"\n💾 Results saved to {output}")


def main():
    import argparse

    parser = argparse.ArgumentParser(description="Omnixform Benchmark Suite")
    parser.add_argument("-i", "--iterations", type=int, default=5, help="Iterations per test")
    parser.add_argument("-o", "--output", type=Path, help="Output JSON file")
    parser.add_argument("--quick", action="store_true", help="Run with fewer iterations")
    args = parser.parse_args()

    if args.quick:
        args.iterations = 3

    print("🚀 Omnixform Exploratory Benchmark Suite")
    print("Results are local diagnostics, not release performance claims.")
    print(f"Running {args.iterations} iterations per test...\n")

    results = run_all_benchmarks(args.iterations)
    print_results(results)

    if args.output:
        save_results(results, args.output)


if __name__ == "__main__":
    main()
