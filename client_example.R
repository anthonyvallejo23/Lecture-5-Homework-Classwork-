library(httr2)

text <- "I met Prof. Charles Malone at University of Colorado in Denver, CO. Email me at malonec2@uoc.edu."

# POST JSON to the redaction endpoint. Emails are always redacted by the API.
req <- request("http://127.0.0.1:5000/api/redact") |>
  req_method("POST") |>
  req_body_json(list(
    text = text,
    types = c("PER", "LOC", "ORG", "MISC")
  ))

response <- req_perform(req)
result <- resp_body_json(response)

cat("Original text:\n", text, "\n\n", sep = "")
cat("Redacted text:\n", result$redacted_text, "\n", sep = "")

print(result$entities)

