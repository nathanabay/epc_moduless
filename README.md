# EPC Modules for ERPNext

Comprehensive EPC (Engineering, Procurement, and Construction) project management module for ERPNext.

## Features

- **Polymorphic Project Management**: Support for Electromechanical, Civil, and Standard/Service project typologies
- **Dynamic WBS**: Equipment-Based, Phase-Based, and Milestone-Based work breakdown structures
- **Dual-Track Billing**: Running Account (RA) Billing and Milestone-based billing
- **Quality Management**: ISO 9001:2015 compliant inspection and test plans
- **IS 456:2000 Compliance**: Concrete mix design and testing management
- **Advanced Construction Features**: Risk management, subcontractor management, HSE tracking
- **Document Control**: Comprehensive document management with RFI and submittal tracking

## Installation

### Prerequisites

- Frappe Framework v15 or higher
- ERPNext v15 or higher

### Steps

1. Navigate to your Frappe bench:
```bash
cd /path/to/frappe-bench
```

2. Get the app:
```bash
bench get-app epc_modules /path/to/epc_modules
```

3. Install on your site:
```bash
bench --site [site-name] install-app epc_modules
```

4. For development, enable developer mode:
```bash
bench --site [site-name] set-config developer_mode 1
```

## Project Typologies

### Electromechanical
- High-precision engineering projects
- Technical Bid Evaluation (TBE) required before procurement
- Spatial zone-based inventory management
- Equipment-based WBS architecture

### Civil Construction
- Bulk volumetric work projects
- Measurement Book-based progress tracking
- Bulk warehouse inventory management
- Phase-based WBS architecture

### Standard/Service
- Consulting and service projects
- Simplified interface without material tracking
- Milestone-based billing
- Milestone-based WBS architecture

## Configuration

### Setting Up Typologies

1. Go to: EPC Modules > Project Typologies
2. Create or modify typologies as needed
3. Assign typology to projects

### Custom Fields

Custom fields are automatically loaded from `fixtures/custom_field.json`.

## Development

### Directory Structure

```
epc_modules/
├── epc_modules/
│   ├── __init__.py
│   ├── epc_modules.py
│   ├── hooks.py
│   ├── api/
│   │   ├── __init__.py
│   │   └── project_api.py
│   ├── config/
│   │   └── desktop.py
│   ├── fixtures/
│   │   ├── custom_field.json
│   │   ├── property_setter.json
│   │   └── typology_defaults.json
│   ├── public/
│   │   └── js/
│   │       ├── epc_utils.js
│   │       └── typology_handlers.js
│   ├── tasks/
│   │   ├── __init__.py
│   │   └── schedulers.py
│   ├── tests/
│   │   ├── __init__.py
│   │   ├── test_hooks.py
│   │   └── test_utils.py
│   └── utils/
│       ├── __init__.py
│       └── constants.py
├── pyproject.toml
├── MANIFEST.in
└── README.md
```

### Running Tests

```bash
bench --site [site-name] run-tests --app epc_modules
```

## License

MIT License - see LICENSE file for details.

## Support

For issues and feature requests, please use the GitHub issue tracker.

## Authors

EPC Development Team

## Version

1.0.0