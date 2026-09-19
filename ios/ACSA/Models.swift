import SwiftUI

/// The three verdicts — must match pipeline/verdicts.py exactly.
enum Verdict: String {
    case likelyHuman = "LIKELY_HUMAN"          // green, left
    case humanLikelyScam = "HUMAN_LIKELY_SCAM" // yellow, middle
    case aiScam = "AI_SCAM"                    // red, right

    var color: Color {
        switch self {
        case .likelyHuman: return .green
        case .humanLikelyScam: return .yellow
        case .aiScam: return .red
        }
    }

    /// 0...1 position along the gauge, left to right.
    var position: Double {
        switch self {
        case .likelyHuman: return 0.12
        case .humanLikelyScam: return 0.5
        case .aiScam: return 0.88
        }
    }

    var title: String {
        switch self {
        case .likelyHuman: return "Likely human"
        case .humanLikelyScam: return "Human, likely scam"
        case .aiScam: return "AI scam"
        }
    }
}

/// Mirrors GET /results/latest. Decoded with .convertFromSnakeCase; unknown keys (e.g. `layers`) are ignored.
struct CallState: Decodable, Equatable {
    var status: String
    var callSid: String?
    var fromNumber: String?
    var callerDisplay: String?
    var greetingText: String?
    var transcript: String?
    var statedName: String?
    var verdict: String?
    var decidedBy: String?
    var explanation: String?

    var verdictKind: Verdict? { verdict.flatMap(Verdict.init(rawValue:)) }
    var isTerminal: Bool { ["done", "declined", "error"].contains(status) }
}
