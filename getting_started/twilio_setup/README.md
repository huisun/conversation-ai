# Twilio Setup Wizard

A web-based setup wizard to help you create the Memory Store and Conversation Configuration required for Twilio Agent Connect.

> **Note**: This wizard is optional. You can also create a Memory Store and Conversation Configuration manually through the [Twilio Console](https://1console.twilio.com) if you prefer.

## Overview

Before using TAC, you need to set up two Twilio services:

1. **Memory Store** - Stores conversation memories, observations, and user profiles
2. **Conversation Configuration** - Manages conversations and participants

This wizard automates the creation of these services using your Twilio credentials.

## Prerequisites

You'll need the following from your [Twilio Console](https://1console.twilio.com):

- **Account SID** - Found on your Console dashboard (starts with `AC`)
- **Auth Token** - Found on your Console dashboard
- **API Key SID** - Create at Console > Account > API keys & tokens (starts with `SK`)
- **API Secret** - Shown only once when creating the API key

## Usage

```bash
# From the repository root
make setup
```

Then open http://localhost:8080 in your browser.

## What It Does

1. Validates your Twilio credentials
2. Creates a Memory Store
3. Creates a test Profile with your contact info (for verifying the setup works)
4. Creates a Conversation Configuration
5. Returns the service IDs to add to your `.env` file
