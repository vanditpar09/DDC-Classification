// Local macOS Vision adapter. No network access or title/custom-word hints.
import Foundation
import Vision
import ImageIO

func emit(_ value: Any) throws {
    let data = try JSONSerialization.data(withJSONObject: value, options: [.sortedKeys])
    print(String(decoding: data, as: UTF8.self))
}

do {
    let request = VNRecognizeTextRequest()
    request.recognitionLevel = .accurate
    request.usesLanguageCorrection = false
    let supported = try request.supportedRecognitionLanguages()
    if CommandLine.arguments.count == 2 && CommandLine.arguments[1] == "--languages" {
        try emit(["languages": supported])
    } else {
        guard CommandLine.arguments.count >= 3 else {
            throw NSError(domain: "LocalOCR", code: 1, userInfo: [NSLocalizedDescriptionKey: "Expected image path and comma-separated language codes"])
        }
        let languages = CommandLine.arguments[2].split(separator: ",").map(String.init)
        guard languages.allSatisfy({ supported.contains($0) }) else {
            throw NSError(domain: "LocalOCR", code: 2, userInfo: [NSLocalizedDescriptionKey: "Requested language is unsupported by this Vision installation"])
        }
        request.recognitionLanguages = languages
        let url = URL(fileURLWithPath: CommandLine.arguments[1])
        guard let source = CGImageSourceCreateWithURL(url as CFURL, nil),
              let image = CGImageSourceCreateImageAtIndex(source, 0, nil) else {
            throw NSError(domain: "LocalOCR", code: 3, userInfo: [NSLocalizedDescriptionKey: "Cannot decode image"])
        }
        var crop = CGRect(x: 0, y: 0, width: image.width, height: image.height)
        var detected = false
        if CommandLine.arguments.contains("--crop") {
            let rectangles = VNDetectRectanglesRequest()
            rectangles.minimumConfidence = 0.7
            rectangles.minimumSize = 0.25
            rectangles.minimumAspectRatio = 0.25
            rectangles.maximumAspectRatio = 1.0
            rectangles.maximumObservations = 8
            try VNImageRequestHandler(cgImage: image).perform([rectangles])
            let candidates = (rectangles.results ?? []).filter {
                let area = $0.boundingBox.width * $0.boundingBox.height
                return area >= 0.20 && area <= 0.95
            }
            if let page = candidates.max(by: { $0.boundingBox.width * $0.boundingBox.height < $1.boundingBox.width * $1.boundingBox.height }) {
                let box = page.boundingBox
                // Axis-aligned bounds preserve all detected page corners.
                crop = CGRect(x: box.minX * Double(image.width),
                              y: (1 - box.maxY) * Double(image.height),
                              width: box.width * Double(image.width),
                              height: box.height * Double(image.height)).insetBy(dx: -8, dy: -8)
                crop = crop.intersection(CGRect(x: 0, y: 0, width: image.width, height: image.height)).integral
                detected = true
            }
        }
        guard let working = image.cropping(to: crop) else {
            throw NSError(domain: "LocalOCR", code: 4, userInfo: [NSLocalizedDescriptionKey: "Cannot crop image"])
        }
        try VNImageRequestHandler(cgImage: working).perform([request])
        let lines: [[String: Any]] = (request.results ?? []).compactMap { observation in
            guard let text = observation.topCandidates(1).first else { return nil }
            let box = observation.boundingBox
            return ["text": text.string, "confidence": Double(text.confidence),
                    "left": crop.minX + box.minX * crop.width,
                    "top": crop.minY + (1 - box.maxY) * crop.height,
                    "width": box.width * crop.width, "height": box.height * crop.height]
        }
        try emit(["lines": lines, "page_detected": detected,
                  "crop": [crop.minX, crop.minY, crop.width, crop.height],
                  "languages": languages, "engine": "apple-vision-accurate",
                  "language_correction": false])
    }
} catch {
    fputs("Local Vision OCR failed: \(error.localizedDescription)\n", stderr)
    exit(1)
}
