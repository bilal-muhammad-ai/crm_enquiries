"""Enquiry lifecycle flow — wraps orchestrator for CrewAI Flow compatibility."""

from crm_enquiries.services.enquiry_orchestrator import EnquiryOrchestrator

# Alias for plan compatibility — orchestrator implements the full lifecycle
EnquiryLifecycleFlow = EnquiryOrchestrator
