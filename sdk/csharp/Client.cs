namespace AstrovoxSDK {
    public class Client {
        public string ApiKey { get; set; }
        public string BaseUrl { get; set; }

        public Client(string apiKey, string baseUrl) {
            ApiKey = apiKey;
            BaseUrl = baseUrl;
        }
    }
}

