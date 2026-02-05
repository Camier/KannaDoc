# DataLab API Reference

Technical navigation for the DataLab Marker API documentation.

## Document Taxonomy

Documentation is organized by filename prefixes:
- `api-reference_`: REST API endpoints, parameters, and response schemas
- `docs_`: High-level concepts, architecture, and integration guides
- `platform_`: Authentication, dashboard usage, and team management
- `use-cases_`: Practical examples (e.g., academic PDFs, legal documents)
- `_blog_`: Technical deep-dives, product updates, and benchmarks
- `_terms_`: Legal agreements and privacy policies

## Topic Mapping

| Topic | Reference File |
|-------|----------------|
| Document Conversion (Marker) | `api-reference_marker.md` |
| Polling Result Status | `api-reference_marker-result-check.md` |
| Requesting Upload URLs | `api-reference_files_request-upload-url.md` |
| Listing Available Workflows | `api-reference_list-workflows.md` |
| Creating Custom Workflows | `api-reference_create-workflow.md` |
| Available Step Types | `api-reference_list-step-types.md` |
| API Health & Connectivity | `api-reference_health.md` |

## API Endpoint

```
Base URL: https://www.datalab.to/api/v1/
Auth: Bearer token (stored in data/.datalab_api_key)
```

## Key Endpoints

### Marker Conversion

```http
POST /marker
Content-Type: multipart/form-data

file: <PDF binary>
output_format: json,html,markdown,chunks
disable_image_extraction: false
extraction_schema: <JSON schema>
add_block_ids: true
```

### Result Polling

```http
GET /marker/{request_id}/result

Response:
{
  "status": "complete|processing|error",
  "result": { ... }
}
```

## Deprecated Parameters

The Marker API has transitioned to a "model-first" approach. These parameters are **DEPRECATED** and ignored:

- **OCR**: `ocr`, `languages`, `math_recognition` (handled automatically)
- **Layout**: `line_formatting`, `block_correction`
- **Processing**: `table_recognition` (unified extraction flow)

## Correct API Request

```python
output_format="json,html,markdown,chunks"  # html required for images
disable_image_extraction=False
disable_image_captions=False
add_block_ids=True  # Only when html in output_format
```

## Rate Limits

- **Free tier**: 100 requests/day
- **Paid tier**: Higher limits (check dashboard)
- **Backoff**: Exponential backoff on 429 responses

## Source Documentation

Full scraped documentation available at:
```
/LAB/@thesis/datalab/datalab_doc/
```

**Scrape Date**: January 2026

**Note**: Do not attempt to access external URLs from within these documents.
