/*
 Podcast video scanner for macOS.

 Purpose
 - Sample frames across a video and detect likely visual boundaries.
 - Identify likely interstitial/title-card moments and likely non-host inserts.
 - Generate review artifacts for editing: CSV files, thumbnails, and an HTML report.

 Usage
   swift scripts/scan_podcast.swift <input-video> <output-dir> [sample-interval-seconds]

 Example
   swift scripts/scan_podcast.swift "episode-006-draft.mp4" dist/analysis/ep006/scan 0.5

 Outputs
 - summary.txt: high-level scan stats
 - boundaries.csv: all detected boundary candidates
 - interstitial_candidates.csv: likely title cards / interstitials
 - non_host_candidates.csv: likely non-host starts (currently includes interstitials too)
 - report.html: visual report for manual review
 - thumbs/: JPEG thumbnails for each candidate frame

 Heuristics
 - Uses frame-to-frame fingerprint differences to find candidate cuts.
 - Uses Vision OCR to detect text-heavy frames.
 - Uses Vision face detection to distinguish host shots from cards / inserts.
 - Labels frames as cut, interstitial, or non-host based on text duration,
   face size/count, and boundary strength.

 Notes
 - macOS only: depends on AVFoundation, Vision, and AppKit.
 - Intended as a fast heuristic pass, not a source of ground-truth edit points.
 - OCR can be noisy; use report.html for human verification.
 - Lower sample intervals improve accuracy but increase runtime.
*/
import Foundation
import AVFoundation
import Vision
import AppKit

struct Sample {
    let time: Double
    let diff: Double
    let fingerprint: [UInt8]
}

struct FrameAnalysis {
    let time: Double
    let faceCount: Int
    let maxFaceArea: Double
    let text: String
    let textCharCount: Int
}

struct BoundaryAnalysis {
    let time: Double
    let timecode: String
    let diff: Double
    let faceCount: Int
    let maxFaceArea: Double
    let text: String
    let textCharCount: Int
    let textDuration: Double
    let nonHostDuration: Double
    let label: String
    let thumbPath: String
}

func usage() {
    let exe = URL(fileURLWithPath: CommandLine.arguments[0]).lastPathComponent
    print("usage: \(exe) <input-video> <output-dir> [sample-interval-seconds]")
}

func timecode(_ seconds: Double) -> String {
    let totalMs = Int((seconds * 1000.0).rounded())
    let ms = totalMs % 1000
    let total = totalMs / 1000
    let s = total % 60
    let m = (total / 60) % 60
    let h = total / 3600
    return String(format: "%02d:%02d:%02d.%03d", h, m, s, ms)
}

func safeFilenameTimecode(_ seconds: Double) -> String {
    timecode(seconds).replacingOccurrences(of: ":", with: "-")
}

func percentile(_ values: [Double], _ p: Double) -> Double {
    guard !values.isEmpty else { return 0 }
    let sorted = values.sorted()
    let idx = min(max(Int(Double(sorted.count - 1) * p), 0), sorted.count - 1)
    return sorted[idx]
}

func htmlEscaped(_ s: String) -> String {
    s.replacingOccurrences(of: "&", with: "&amp;")
        .replacingOccurrences(of: "<", with: "&lt;")
        .replacingOccurrences(of: ">", with: "&gt;")
        .replacingOccurrences(of: "\"", with: "&quot;")
}

func csvEscaped(_ s: String) -> String {
    let cleaned = s.replacingOccurrences(of: "\n", with: " ")
    return "\"" + cleaned.replacingOccurrences(of: "\"", with: "\"\"") + "\""
}

func fingerprint(_ cg: CGImage, width: Int = 16, height: Int = 16) -> [UInt8] {
    let colorSpace = CGColorSpaceCreateDeviceGray()
    var data = [UInt8](repeating: 0, count: width * height)
    data.withUnsafeMutableBytes { buf in
        if let ctx = CGContext(
            data: buf.baseAddress,
            width: width,
            height: height,
            bitsPerComponent: 8,
            bytesPerRow: width,
            space: colorSpace,
            bitmapInfo: 0
        ) {
            ctx.interpolationQuality = .low
            ctx.draw(cg, in: CGRect(x: 0, y: 0, width: width, height: height))
        }
    }
    return data
}

func meanAbsDiff(_ a: [UInt8], _ b: [UInt8]) -> Double {
    guard a.count == b.count, !a.isEmpty else { return 0 }
    var total = 0.0
    for i in 0..<a.count {
        total += abs(Double(a[i]) - Double(b[i])) / 255.0
    }
    return total / Double(a.count)
}

func saveJPEG(_ cg: CGImage, to url: URL, compression: Double = 0.72) throws {
    let rep = NSBitmapImageRep(cgImage: cg)
    guard let data = rep.representation(using: .jpeg, properties: [.compressionFactor: compression]) else {
        throw NSError(domain: "scan_podcast", code: 1, userInfo: [NSLocalizedDescriptionKey: "Could not encode JPEG"])
    }
    try data.write(to: url)
}

func detectFacesAndText(_ cg: CGImage) throws -> (Int, Double, String, Int) {
    let faceRequest = VNDetectFaceRectanglesRequest()
    let textRequest = VNRecognizeTextRequest()
    textRequest.recognitionLevel = .fast
    textRequest.usesLanguageCorrection = true

    let handler = VNImageRequestHandler(cgImage: cg, options: [:])
    try handler.perform([faceRequest, textRequest])

    let faces = faceRequest.results ?? []
    let faceCount = faces.count
    let maxFaceArea = faces.map { Double($0.boundingBox.width * $0.boundingBox.height) }.max() ?? 0.0

    let lines = (textRequest.results ?? []).compactMap { observation in
        observation.topCandidates(1).first?.string
    }
    let text = lines.joined(separator: " | ")
    let textCharCount = text.replacingOccurrences(of: " ", with: "").count

    return (faceCount, maxFaceArea, text, textCharCount)
}

if CommandLine.arguments.count < 3 {
    usage()
    exit(1)
}

let inputPath = CommandLine.arguments[1]
let outputDir = URL(fileURLWithPath: CommandLine.arguments[2], isDirectory: true)
let interval = Double(CommandLine.arguments.count >= 4 ? CommandLine.arguments[3] : "0.5") ?? 0.5

let fm = FileManager.default
try fm.createDirectory(at: outputDir, withIntermediateDirectories: true)
let thumbsDir = outputDir.appendingPathComponent("thumbs", isDirectory: true)
try fm.createDirectory(at: thumbsDir, withIntermediateDirectories: true)

let asset = AVURLAsset(url: URL(fileURLWithPath: inputPath))
let durationSeconds = CMTimeGetSeconds(asset.duration)
let frameGenerator = AVAssetImageGenerator(asset: asset)
frameGenerator.appliesPreferredTrackTransform = true
frameGenerator.maximumSize = CGSize(width: 160, height: 90)
frameGenerator.requestedTimeToleranceBefore = .zero
frameGenerator.requestedTimeToleranceAfter = .zero

print("Sampling \(inputPath) every \(interval)s…")
let sampleCount = Int(floor(durationSeconds / interval)) + 1
var samples: [Sample] = []
samples.reserveCapacity(sampleCount)
var previousFingerprint: [UInt8]? = nil
let scanStart = Date()

for i in 0..<sampleCount {
    autoreleasepool {
        let time = Double(i) * interval
        let cmTime = CMTime(seconds: time, preferredTimescale: 600)
        do {
            let cg = try frameGenerator.copyCGImage(at: cmTime, actualTime: nil)
            let fp = fingerprint(cg)
            let diff = previousFingerprint.map { meanAbsDiff($0, fp) } ?? 0.0
            samples.append(Sample(time: time, diff: diff, fingerprint: fp))
            previousFingerprint = fp
        } catch {
            fputs("warning: could not sample at \(timecode(time)): \(error)\n", stderr)
        }
        if i > 0 && i % 500 == 0 {
            print("  sampled \(i)/\(sampleCount) frames")
        }
    }
}

let scanElapsed = Date().timeIntervalSince(scanStart)
let diffs = samples.dropFirst().map { $0.diff }
let p95 = percentile(diffs, 0.95)
let p98 = percentile(diffs, 0.98)
let p99 = percentile(diffs, 0.99)
let boundaryThreshold = max(0.12, p98)
let scanElapsedString = String(format: "%.1f", scanElapsed)
let p95String = String(format: "%.4f", p95)
let p98String = String(format: "%.4f", p98)
let p99String = String(format: "%.4f", p99)
let boundaryThresholdString = String(format: "%.4f", boundaryThreshold)

print("Done sampling in \(scanElapsedString)s")
print("Diff percentiles: p95=\(p95String) p98=\(p98String) p99=\(p99String)")
print("Boundary threshold: \(boundaryThresholdString)")

var candidateSamples: [Sample] = []
if let first = samples.first {
    candidateSamples.append(first)
}
for i in 1..<(samples.count - 1) {
    let current = samples[i]
    if current.diff < boundaryThreshold { continue }
    if current.diff < samples[i - 1].diff { continue }
    if current.diff < samples[i + 1].diff { continue }
    if let last = candidateSamples.last, current.time - last.time < 2.0 {
        continue
    }
    candidateSamples.append(current)
}

print("Selected \(candidateSamples.count) boundary candidates")

let detailGenerator = AVAssetImageGenerator(asset: asset)
detailGenerator.appliesPreferredTrackTransform = true
detailGenerator.maximumSize = CGSize(width: 640, height: 360)
detailGenerator.requestedTimeToleranceBefore = .zero
detailGenerator.requestedTimeToleranceAfter = .zero

var frameCache: [String: FrameAnalysis] = [:]
let cacheKeyPrecision = 3

func cacheKey(_ time: Double) -> String {
    String(format: "%0.*f", cacheKeyPrecision, time)
}

func analyzeFrame(at time: Double) throws -> FrameAnalysis {
    let clamped = max(0.0, min(durationSeconds, time))
    let key = cacheKey(clamped)
    if let cached = frameCache[key] {
        return cached
    }
    let cg = try detailGenerator.copyCGImage(at: CMTime(seconds: clamped, preferredTimescale: 600), actualTime: nil)
    let (faceCount, maxFaceArea, text, textCharCount) = try detectFacesAndText(cg)
    let analysis = FrameAnalysis(time: clamped, faceCount: faceCount, maxFaceArea: maxFaceArea, text: text, textCharCount: textCharCount)
    frameCache[key] = analysis
    return analysis
}

func estimateRun(start: Double, maxDuration: Double, predicate: (FrameAnalysis) -> Bool) -> Double {
    var matched = false
    var lastMatchTime = start
    var t = start
    while t <= min(durationSeconds, start + maxDuration) {
        do {
            let frame = try analyzeFrame(at: t)
            if predicate(frame) {
                matched = true
                lastMatchTime = t
            } else if matched {
                break
            }
        } catch {
            break
        }
        t += interval
    }
    return matched ? max(interval, lastMatchTime - start + interval) : 0.0
}

func labelFor(diff: Double, frame: FrameAnalysis, textDuration: Double, nonHostDuration: Double) -> String {
    let textLike = frame.textCharCount >= 14
    let largeFace = frame.maxFaceArea >= 0.04
    let noLargeFace = frame.maxFaceArea < 0.03

    if textLike && !largeFace && textDuration > 0.0 && textDuration <= 15.0 {
        return "interstitial"
    }
    if textLike && nonHostDuration >= interval {
        return "non-host"
    }
    if noLargeFace && diff >= max(0.16, p99 * 0.8) && nonHostDuration >= 1.0 {
        return "non-host"
    }
    return "cut"
}

var analyses: [BoundaryAnalysis] = []
analyses.reserveCapacity(candidateSamples.count)

for (index, sample) in candidateSamples.enumerated() {
    autoreleasepool {
        do {
            let cg = try detailGenerator.copyCGImage(at: CMTime(seconds: sample.time, preferredTimescale: 600), actualTime: nil)
            let frame = try detectFacesAndText(cg)
            let frameAnalysis = FrameAnalysis(time: sample.time, faceCount: frame.0, maxFaceArea: frame.1, text: frame.2, textCharCount: frame.3)
            frameCache[cacheKey(sample.time)] = frameAnalysis

            let textDuration = estimateRun(start: sample.time, maxDuration: 15.0) { frame in
                frame.textCharCount >= 14
            }
            let nonHostDuration = estimateRun(start: sample.time, maxDuration: 30.0) { frame in
                frame.textCharCount >= 14 || frame.maxFaceArea < 0.03
            }
            let label = labelFor(diff: sample.diff, frame: frameAnalysis, textDuration: textDuration, nonHostDuration: nonHostDuration)

            let thumbName = String(format: "%03d_%@_%@.jpg", index + 1, label, safeFilenameTimecode(sample.time))
            let thumbURL = thumbsDir.appendingPathComponent(thumbName)
            try saveJPEG(cg, to: thumbURL)

            analyses.append(BoundaryAnalysis(
                time: sample.time,
                timecode: timecode(sample.time),
                diff: sample.diff,
                faceCount: frameAnalysis.faceCount,
                maxFaceArea: frameAnalysis.maxFaceArea,
                text: frameAnalysis.text,
                textCharCount: frameAnalysis.textCharCount,
                textDuration: textDuration,
                nonHostDuration: nonHostDuration,
                label: label,
                thumbPath: "thumbs/\(thumbName)"
            ))
        } catch {
            fputs("warning: boundary analysis failed at \(timecode(sample.time)): \(error)\n", stderr)
        }
    }
}

analyses.sort { $0.time < $1.time }
let interstitials = analyses.filter { $0.label == "interstitial" }
let nonHost = analyses.filter { $0.label == "interstitial" || $0.label == "non-host" }

var boundariesCSV = "time_seconds,timecode,label,diff,face_count,max_face_area,text_char_count,text_duration,non_host_duration,text,thumb_path\n"
for item in analyses {
    boundariesCSV += [
        String(format: "%.3f", item.time),
        csvEscaped(item.timecode),
        csvEscaped(item.label),
        String(format: "%.5f", item.diff),
        String(item.faceCount),
        String(format: "%.5f", item.maxFaceArea),
        String(item.textCharCount),
        String(format: "%.2f", item.textDuration),
        String(format: "%.2f", item.nonHostDuration),
        csvEscaped(item.text),
        csvEscaped(item.thumbPath)
    ].joined(separator: ",") + "\n"
}
try boundariesCSV.write(to: outputDir.appendingPathComponent("boundaries.csv"), atomically: true, encoding: .utf8)

func writeFilteredCSV(_ url: URL, _ items: [BoundaryAnalysis]) throws {
    var csv = "time_seconds,timecode,label,diff,text_duration,non_host_duration,face_count,max_face_area,text,thumb_path\n"
    for item in items {
        csv += [
            String(format: "%.3f", item.time),
            csvEscaped(item.timecode),
            csvEscaped(item.label),
            String(format: "%.5f", item.diff),
            String(format: "%.2f", item.textDuration),
            String(format: "%.2f", item.nonHostDuration),
            String(item.faceCount),
            String(format: "%.5f", item.maxFaceArea),
            csvEscaped(item.text),
            csvEscaped(item.thumbPath)
        ].joined(separator: ",") + "\n"
    }
    try csv.write(to: url, atomically: true, encoding: .utf8)
}

try writeFilteredCSV(outputDir.appendingPathComponent("interstitial_candidates.csv"), interstitials)
try writeFilteredCSV(outputDir.appendingPathComponent("non_host_candidates.csv"), nonHost)

let summary = """
Input: \(inputPath)
Duration: \(timecode(durationSeconds))
Sample interval: \(interval)s
Samples: \(samples.count)
Sampling elapsed: \(String(format: "%.1f", scanElapsed))s
Diff threshold: \(String(format: "%.5f", boundaryThreshold))
Boundary candidates: \(analyses.count)
Likely interstitials: \(interstitials.count)
Likely non-host starts: \(nonHost.count)
Output:
- \(outputDir.path)/boundaries.csv
- \(outputDir.path)/interstitial_candidates.csv
- \(outputDir.path)/non_host_candidates.csv
- \(outputDir.path)/report.html
"""
try summary.write(to: outputDir.appendingPathComponent("summary.txt"), atomically: true, encoding: .utf8)

func htmlRows(_ items: [BoundaryAnalysis]) -> String {
    items.map { item in
        let text = item.text.isEmpty ? "&nbsp;" : htmlEscaped(item.text)
        return """
        <tr>
          <td><img src="\(htmlEscaped(item.thumbPath))" loading="lazy"></td>
          <td>
            <div><strong>\(htmlEscaped(item.timecode))</strong></div>
            <div class="pill \(htmlEscaped(item.label))">\(htmlEscaped(item.label))</div>
          </td>
          <td>\(String(format: "%.4f", item.diff))</td>
          <td>\(item.faceCount)</td>
          <td>\(String(format: "%.4f", item.maxFaceArea))</td>
          <td>\(String(format: "%.1fs", item.textDuration))</td>
          <td>\(String(format: "%.1fs", item.nonHostDuration))</td>
          <td class="text">\(text)</td>
        </tr>
        """
    }.joined(separator: "\n")
}

let reportHTML = """
<!doctype html>
<html>
<head>
  <meta charset="utf-8">
  <title>Podcast scan report</title>
  <style>
    body { font-family: -apple-system, BlinkMacSystemFont, sans-serif; margin: 24px; color: #111; }
    h1, h2 { margin: 0 0 12px; }
    p, li { line-height: 1.45; }
    table { border-collapse: collapse; width: 100%; margin: 16px 0 32px; }
    th, td { border: 1px solid #ddd; padding: 8px; vertical-align: top; font-size: 14px; }
    th { position: sticky; top: 0; background: #f7f7f7; text-align: left; }
    img { width: 220px; border-radius: 6px; display: block; }
    .pill { display: inline-block; padding: 2px 8px; border-radius: 999px; font-size: 12px; margin-top: 6px; }
    .interstitial { background: #ffe6a7; }
    .non-host { background: #cdeffd; }
    .cut { background: #ececec; }
    .text { min-width: 320px; max-width: 480px; word-break: break-word; }
    .meta { background: #fafafa; padding: 12px 16px; border-radius: 8px; }
  </style>
</head>
<body>
  <h1>Podcast scan report</h1>
  <div class="meta">
    <p><strong>Input:</strong> \(htmlEscaped(inputPath))</p>
    <p><strong>Duration:</strong> \(htmlEscaped(timecode(durationSeconds)))</p>
    <p><strong>Sample interval:</strong> \(interval)s</p>
    <p><strong>Diff threshold:</strong> \(String(format: "%.5f", boundaryThreshold))</p>
    <p><strong>Boundary candidates:</strong> \(analyses.count)</p>
    <p><strong>Likely interstitials:</strong> \(interstitials.count)</p>
    <p><strong>Likely non-host starts:</strong> \(nonHost.count)</p>
  </div>

  <h2>Likely interstitials</h2>
  <table>
    <thead>
      <tr><th>Thumbnail</th><th>Time</th><th>Diff</th><th>Faces</th><th>Max face area</th><th>Text duration</th><th>Non-host duration</th><th>OCR text</th></tr>
    </thead>
    <tbody>
      \(htmlRows(interstitials))
    </tbody>
  </table>

  <h2>Likely non-host starts</h2>
  <table>
    <thead>
      <tr><th>Thumbnail</th><th>Time</th><th>Diff</th><th>Faces</th><th>Max face area</th><th>Text duration</th><th>Non-host duration</th><th>OCR text</th></tr>
    </thead>
    <tbody>
      \(htmlRows(nonHost))
    </tbody>
  </table>

  <h2>All boundary candidates</h2>
  <table>
    <thead>
      <tr><th>Thumbnail</th><th>Time</th><th>Diff</th><th>Faces</th><th>Max face area</th><th>Text duration</th><th>Non-host duration</th><th>OCR text</th></tr>
    </thead>
    <tbody>
      \(htmlRows(analyses))
    </tbody>
  </table>
</body>
</html>
"""
try reportHTML.write(to: outputDir.appendingPathComponent("report.html"), atomically: true, encoding: .utf8)

print("Wrote report to \(outputDir.path)")
