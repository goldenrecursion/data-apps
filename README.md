# Data Apps

## Overview
This repository hosts Golden's data applications and demonstrations for submitting data to [Golden's Protocol](https://dapp.golden.xyz).

These applications directly integrate with [Golden's GraphQL API](https://docs.golden.xyz/api/readme-1) and include ML/NLP applications that use named entity recognition models to help programmit cextract entity/triple data.

They are also built with [Godel](https://github.com/goldenrecursion/godel) and [Spacy](https://github.com/explosion/spaCy).

## Streamlit Demo

We've hosted a demo on streamlit that you can checkout at https://data-apps.streamlitapp.com!

It includes pages on:
  - Entity Creation
  - Triple Creation
  - Text to Triples

## Development

### Docker

Build and deploy our demos with docker:

``` 
docker-compose build
docker-compose up
```

Check out the streamlit demo at `localhost:8501`

## Contact

For all things related to `data-apps` and development, please contact the maintainer Andrew Chang at andrew@golden.co or [@achang1618](https://twitter.com/achang1618) for any quesions or comments.

For all other support, please reach out to support@golden.co.

Follow [@golden](https://twitter.com/Golden) to keep up with additional news!

## License

This project is licensed under the terms of the Apache 2.0 license