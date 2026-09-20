import SwiftUI

/// Backend URL setting. Reached from the gear on the splash screen (ngrok's free tier rotates the URL on every restart).
struct SettingsView: View {
    @Environment(\.dismiss) private var dismiss
    @State private var url = APIClient.baseURL

    var body: some View {
        NavigationStack {
            Form {
                Section {
                    TextField("https://xxxx.ngrok-free.app", text: $url)
                        .textInputAutocapitalization(.never).autocorrectionDisabled().keyboardType(.URL)
                } header: {
                    Text("Backend URL")
                } footer: {
                    Text("ngrok's free tier gives a new URL every restart — paste the current one here.")
                }
            }
            .navigationTitle("Settings")
            .toolbar {
                ToolbarItem(placement: .confirmationAction) {
                    Button("Save") { APIClient.baseURL = url; dismiss() }
                }
            }
        }
    }
}
