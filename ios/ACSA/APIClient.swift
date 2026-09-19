import Foundation

enum APIError: LocalizedError {
    case badURL, http(Int)
    var errorDescription: String? {
        switch self {
        case .badURL: return "Backend URL isn't valid"
        case .http(let code): return "Backend returned \(code)"
        }
    }
}

struct APIClient {
    static let defaultsKey = "acsa.baseURL"

    /// Set once in the in-app settings sheet (persisted). ngrok's free tier changes this every restart.
    static var baseURL: String {
        get { UserDefaults.standard.string(forKey: defaultsKey) ?? ProcessInfo.processInfo.environment["ACSA_BASE_URL"] ?? "http://localhost:8000" }
        set { UserDefaults.standard.set(newValue.trimmingCharacters(in: .whitespacesAndNewlines), forKey: defaultsKey) }
    }

    private static func request(_ path: String, method: String = "GET", body: Data? = nil) throws -> URLRequest {
        let trimmed = baseURL.trimmingCharacters(in: CharacterSet(charactersIn: "/ "))
        guard let url = URL(string: trimmed + path) else { throw APIError.badURL }
        var req = URLRequest(url: url, timeoutInterval: 4)
        req.httpMethod = method
        req.httpBody = body
        req.setValue("true", forHTTPHeaderField: "ngrok-skip-browser-warning") // skips ngrok's free-tier interstitial
        if body != nil { req.setValue("application/json", forHTTPHeaderField: "Content-Type") }
        return req
    }

    static func latest() async throws -> CallState? {
        let (data, resp) = try await URLSession.shared.data(for: request("/results/latest"))
        if let http = resp as? HTTPURLResponse, http.statusCode != 200 { throw APIError.http(http.statusCode) }
        let decoder = JSONDecoder()
        decoder.keyDecodingStrategy = .convertFromSnakeCase
        let state = try decoder.decode(CallState.self, from: data)
        return state.callSid == nil ? nil : state // {"status":"waiting"} = no calls yet
    }

    /// Yes/No bubble. Yes -> ACSA answers; No -> the backend rings the call through (or declines).
    static func decide(answer: Bool, callSid: String) async throws {
        let body = try JSONSerialization.data(withJSONObject: ["answer": answer, "call_sid": callSid])
        let (_, resp) = try await URLSession.shared.data(for: request("/call/decision", method: "POST", body: body))
        if let http = resp as? HTTPURLResponse, !(200..<300).contains(http.statusCode), http.statusCode != 409 {
            throw APIError.http(http.statusCode) // 409 = call already moved on (e.g. hold timed out); fine
        }
    }
}
