#!/usr/bin/env python3
import whois
import sys

if len(sys.argv) > 1:
    domain = sys.argv[1]
    try:
        w = whois.whois(domain)
        print(w)
    except Exception as e:
        print(f"Error: {e}")
else:
    print("Usage: whois_wrapper.py <domain>")
