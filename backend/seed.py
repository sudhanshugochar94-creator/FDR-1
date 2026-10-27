import asyncio
from datetime import date, datetime, timedelta
from decimal import Decimal
import uuid
from sqlalchemy import delete, select
from app.config import settings
from app.core.security import hash_password
from app.database import Base, initialize_database
from app.models.audit import AuditEvent
from app.models.document import DocumentUploadType, FDRDocument
from app.models.duplicate import DuplicateCandidate, DuplicateStatus
from app.models.extraction import ExtractionMethod, ExtractionResult
from app.models.fdr import FDRInstrument, FDRStatus, VerificationStatus
from app.models.institution import Institution
from app.models.lifecycle import (
    LifecycleRelationship,
    LifecycleRelationshipType,
    ReleaseRequest,
    ReleaseStatus,
    RenewalRequest,
    RenewalStatus,
)
from app.models.notification import Notification, NotificationType
from app.models.review import (
    ReviewAssignment,
    ReviewAssignmentStatus,
    ReviewObservation,
    ReviewObservationType,
)
from app.models.system_config import SystemConfiguration
from app.models.user import User, UserRole
from app.models.user_institution_role import UserInstitutionRole
from app.models.validation import FindingSeverity, FindingType, ValidationFinding
from app.models.verification import VerificationRecord, VerificationResult, VerificationType


async def seed_database() -> None:
    print("Starting FDR Portal database seeding...")
    await initialize_database()
    from app.database import async_session_maker, engine

    # Ensure schema tables exist
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    print("[OK] Database schema verified/created.")

    async with async_session_maker() as session:
        # Check if already seeded (idempotency check)
        existing_users = await session.execute(select(User))
        if existing_users.scalars().first():
            print("Existing records found. Cleaning up data for a clean reseed...")
            for model in [
                AuditEvent,
                Notification,
                ReleaseRequest,
                RenewalRequest,
                LifecycleRelationship,
                ReviewObservation,
                ReviewAssignment,
                VerificationRecord,
                DuplicateCandidate,
                ValidationFinding,
                ExtractionResult,
                FDRDocument,
                FDRInstrument,
                UserInstitutionRole,
                SystemConfiguration,
                User,
                Institution,
            ]:
                await session.execute(delete(model))
            await session.commit()
            print("[OK] Cleanup completed.")

        # -------------------------------------------------------------
        # 1. Create Institutions
        # -------------------------------------------------------------
        print("Creating institutions...")
        inst1 = Institution(
            id=uuid.uuid4(),
            name="National Institute of Technology - Demo",
            code="INST-001",
            address="Campus Sector 4, Knowledge Park",
            city="New Delhi",
            state="Delhi",
            contact_email="registrar@nitdemo.ac.in",
            contact_phone="+91-11-23456789",
            is_active=True,
        )
        inst2 = Institution(
            id=uuid.uuid4(),
            name="Demo Engineering College",
            code="INST-002",
            address="Survey 45/2, Electronic City Phase 1",
            city="Bengaluru",
            state="Karnataka",
            contact_email="finance@demoengg.edu",
            contact_phone="+91-80-41239876",
            is_active=True,
        )
        inst3 = Institution(
            id=uuid.uuid4(),
            name="Sample University of Science",
            code="INST-003",
            address="University Hills, Raj Bhavan Road",
            city="Hyderabad",
            state="Telangana",
            contact_email="director@sampleuni.ac.in",
            contact_phone="+91-40-66778899",
            is_active=True,
        )
        session.add_all([inst1, inst2, inst3])
        await session.flush()
        print(f"[OK] 3 institutions created: {inst1.code}, {inst2.code}, {inst3.code}")

        # -------------------------------------------------------------
        # 2. Create Users
        # -------------------------------------------------------------
        print("Creating users...")
        user_admin = User(
            id=uuid.uuid4(),
            email="admin@fdrportal.demo",
            username="admin",
            hashed_password=hash_password("Admin@123"),
            full_name="Compliance Administrator",
            role=UserRole.ADMIN,
            is_active=True,
        )
        user_reviewer = User(
            id=uuid.uuid4(),
            email="reviewer@fdrportal.demo",
            username="reviewer",
            hashed_password=hash_password("Reviewer@123"),
            full_name="Senior FDR Reviewer",
            role=UserRole.REVIEWER,
            is_active=True,
        )
        user_approver = User(
            id=uuid.uuid4(),
            email="approver@fdrportal.demo",
            username="approver",
            hashed_password=hash_password("Approver@123"),
            full_name="Approving Authority Officer",
            role=UserRole.APPROVING_AUTHORITY,
            is_active=True,
        )
        user_inst1 = User(
            id=uuid.uuid4(),
            email="inst1@fdrportal.demo",
            username="inst1",
            hashed_password=hash_password("Institute1@123"),
            full_name="Nodal Officer - NIT Demo",
            role=UserRole.INSTITUTION_USER,
            is_active=True,
        )
        user_inst2 = User(
            id=uuid.uuid4(),
            email="inst2@fdrportal.demo",
            username="inst2",
            hashed_password=hash_password("Institute2@123"),
            full_name="Accounts Officer - Demo Engg",
            role=UserRole.INSTITUTION_USER,
            is_active=True,
        )
        session.add_all([user_admin, user_reviewer, user_approver, user_inst1, user_inst2])
        await session.flush()

        # Link institution users
        role_inst1 = UserInstitutionRole(
            user_id=user_inst1.id,
            institution_id=inst1.id,
            role_title="Nodal Compliance Officer",
            is_primary=True,
        )
        role_inst2 = UserInstitutionRole(
            user_id=user_inst2.id,
            institution_id=inst2.id,
            role_title="Senior Finance Manager",
            is_primary=True,
        )
        session.add_all([role_inst1, role_inst2])
        await session.flush()
        print("[OK] 5 users created with role mappings.")

        # -------------------------------------------------------------
        # 3. Create Sample FDR Records Matching Scenarios A-F
        # -------------------------------------------------------------
        today = date.today()

        # SCENARIO A: Standard clean, active, verified FDR
        fdr_a = FDRInstrument(
            id=uuid.uuid4(),
            institution_id=inst1.id,
            internal_reference="FDR-2026-0001",
            application_number="APP-NIT-2024-001",
            bank_name="State Bank of India",
            branch_name="Main Campus Branch",
            fdr_number="SBI-FDR-98234110",
            deposit_amount=Decimal("5000000.00"),
            currency="INR",
            issue_date=date(2024, 1, 15),
            maturity_date=date(2027, 1, 15),
            status=FDRStatus.ACTIVE,
            verification_status=VerificationStatus.VERIFIED,
            review_priority_score=10,
            review_priority_reasons=["Standard compliance", "All extracted fields match bank record"],
            has_potential_duplicate=False,
            compliance_reference="SEC-DEP-ENGG-2024",
            notes="Mandatory endowment security deposit for PG Engineering department.",
            submitted_by=user_inst1.id,
            assigned_reviewer_id=user_reviewer.id,
        )
        session.add(fdr_a)
        await session.flush()

        doc_a = FDRDocument(
            fdr_instrument_id=fdr_a.id,
            original_filename="sbi_fixed_deposit_receipt.pdf",
            stored_filename=f"doc_{uuid.uuid4().hex[:12]}_sbi_fd.pdf",
            file_path=f"{settings.UPLOAD_DIR}/doc_sbi_fd.pdf",
            file_size=245890,
            mime_type="application/pdf",
            file_hash_sha256="4a5b6c7d8e9f0123456789abcdef0123456789abcdef0123456789abcdef0123",
            upload_type=DocumentUploadType.ORIGINAL,
            uploaded_by=user_inst1.id,
        )
        session.add(doc_a)
        await session.flush()

        ext_a = ExtractionResult(
            document_id=doc_a.id,
            extraction_method=ExtractionMethod.TEXT_EXTRACTION,
            raw_text="STATE BANK OF INDIA\nFIXED DEPOSIT RECEIPT\nAccount No: SBI-FDR-98234110\nAmount: Rs. 50,00,000/- (Fifty Lakhs Only)\nIssue Date: 15/01/2024\nMaturity Date: 15/01/2027\nBeneficiary: National Institute of Technology - Demo",
            extracted_fields={
                "fdr_number": "SBI-FDR-98234110",
                "bank_name": "State Bank of India",
                "deposit_amount": 5000000.00,
                "currency": "INR",
                "issue_date": "2024-01-15",
                "maturity_date": "2027-01-15",
                "beneficiary": "National Institute of Technology - Demo",
            },
            confidence_scores={
                "fdr_number": 0.99,
                "deposit_amount": 0.98,
                "dates": 0.97,
            },
            ai_model_used="pymupdf-native",
            processing_time_ms=145,
        )
        session.add(ext_a)

        val_a1 = ValidationFinding(
            fdr_instrument_id=fdr_a.id,
            field_name="fdr_number",
            submitted_value="SBI-FDR-98234110",
            extracted_value="SBI-FDR-98234110",
            finding_type=FindingType.MATCH,
            severity=FindingSeverity.INFO,
            description="Instrument number matches exactly.",
        )
        val_a2 = ValidationFinding(
            fdr_instrument_id=fdr_a.id,
            field_name="deposit_amount",
            submitted_value="5000000.00",
            extracted_value="5000000.00",
            finding_type=FindingType.MATCH,
            severity=FindingSeverity.INFO,
            description="Deposit amount verified across form and receipt.",
        )
        session.add_all([val_a1, val_a2])

        ver_a = VerificationRecord(
            fdr_instrument_id=fdr_a.id,
            verified_by=user_reviewer.id,
            verification_type=VerificationType.DOCUMENT_CHECK,
            result=VerificationResult.VERIFIED,
            notes="Document authentic with bank watermark and matching signature.",
            evidence_summary="Extracted metadata verified against physical PDF headers.",
        )
        session.add(ver_a)

        # SCENARIO B: Validation mismatch / Discrepancy (Correction Requested)
        fdr_b = FDRInstrument(
            id=uuid.uuid4(),
            institution_id=inst1.id,
            internal_reference="FDR-2026-0002",
            application_number="APP-NIT-2025-042",
            bank_name="HDFC Bank",
            branch_name="Koramangala Branch",
            fdr_number="HDFC-771200456",
            deposit_amount=Decimal("2500000.00"),  # Form says 25 Lakhs
            currency="INR",
            issue_date=date(2025, 6, 10),
            maturity_date=date(2028, 6, 10),
            status=FDRStatus.CORRECTION_REQUESTED,
            verification_status=VerificationStatus.PENDING,
            review_priority_score=85,
            review_priority_reasons=[
                "Deposit amount mismatch of ₹5,00,000 between submission and document",
                "Branch name mismatch detected",
            ],
            has_potential_duplicate=False,
            compliance_reference="SEC-DEP-CSE-2025",
            notes="Endowment deposit for Computer Science intake expansion.",
            submitted_by=user_inst1.id,
            assigned_reviewer_id=user_reviewer.id,
        )
        session.add(fdr_b)
        await session.flush()

        doc_b = FDRDocument(
            fdr_instrument_id=fdr_b.id,
            original_filename="hdfc_fd_receipt_scan.pdf",
            stored_filename=f"doc_{uuid.uuid4().hex[:12]}_hdfc.pdf",
            file_path=f"{settings.UPLOAD_DIR}/doc_hdfc.pdf",
            file_size=512040,
            mime_type="application/pdf",
            file_hash_sha256="1234567890abcdef1234567890abcdef1234567890abcdef1234567890abcdef",
            upload_type=DocumentUploadType.ORIGINAL,
            uploaded_by=user_inst1.id,
        )
        session.add(doc_b)
        await session.flush()

        ext_b = ExtractionResult(
            document_id=doc_b.id,
            extraction_method=ExtractionMethod.OCR,
            raw_text="HDFC BANK LTD\nTERM DEPOSIT CONFIRMATION\nFDR No: HDFC-771200456\nPrincipal: Rs. 20,00,000.00\nBranch: Indiranagar Branch\nTenure: 36 Months",
            extracted_fields={
                "fdr_number": "HDFC-771200456",
                "bank_name": "HDFC Bank",
                "deposit_amount": 2000000.00,  # Document says 20 Lakhs!
                "branch_name": "Indiranagar Branch",
            },
            confidence_scores={
                "deposit_amount": 0.94,
                "fdr_number": 0.96,
                "branch_name": 0.91,
            },
            ai_model_used="tesseract-ocr",
            processing_time_ms=830,
        )
        session.add(ext_b)

        val_b1 = ValidationFinding(
            fdr_instrument_id=fdr_b.id,
            field_name="deposit_amount",
            submitted_value="2500000.00",
            extracted_value="2000000.00",
            finding_type=FindingType.MISMATCH,
            severity=FindingSeverity.CRITICAL,
            description="Submitted amount ₹25,00,000 exceeds uploaded document amount ₹20,00,000 by ₹5,00,000.",
        )
        val_b2 = ValidationFinding(
            fdr_instrument_id=fdr_b.id,
            field_name="branch_name",
            submitted_value="Koramangala Branch",
            extracted_value="Indiranagar Branch",
            finding_type=FindingType.MISMATCH,
            severity=FindingSeverity.WARNING,
            description="Branch stated on receipt differs from submission details.",
        )
        session.add_all([val_b1, val_b2])

        obs_b = ReviewObservation(
            fdr_instrument_id=fdr_b.id,
            observer_id=user_reviewer.id,
            observation_type=ReviewObservationType.CORRECTION_REQUEST,
            content="Please clarify the ₹5,00,000 discrepancy between the form (₹25L) and receipt (₹20L), or re-upload the correct certificate.",
        )
        session.add(obs_b)

        # SCENARIO C: Potential Duplicate FDR Detected
        fdr_c1 = FDRInstrument(
            id=uuid.uuid4(),
            institution_id=inst2.id,
            internal_reference="FDR-2026-0003",
            application_number="APP-DEC-2024-088",
            bank_name="ICICI Bank",
            branch_name="Shivaji Nagar Branch",
            fdr_number="ICICI-88239011",
            deposit_amount=Decimal("3000000.00"),
            currency="INR",
            issue_date=date(2024, 9, 1),
            maturity_date=date(2027, 9, 1),
            status=FDRStatus.UNDER_REVIEW,
            verification_status=VerificationStatus.PENDING,
            review_priority_score=95,
            review_priority_reasons=[
                "Duplicate instrument number matched across another institution application",
                "High cryptographic document hash overlap",
            ],
            has_potential_duplicate=True,
            compliance_reference="SEC-DEP-MECH-2024",
            notes="Endowment deposit for Mechanical Engineering program.",
            submitted_by=user_inst2.id,
            assigned_reviewer_id=user_reviewer.id,
        )
        fdr_c2 = FDRInstrument(
            id=uuid.uuid4(),
            institution_id=inst3.id,
            internal_reference="FDR-2026-0004",
            application_number="APP-SUS-2024-012",
            bank_name="ICICI Bank",
            branch_name="Shivaji Nagar Branch",
            fdr_number="ICICI-88239011",  # Same bank FDR number
            deposit_amount=Decimal("3000000.00"),
            currency="INR",
            issue_date=date(2024, 9, 1),
            maturity_date=date(2027, 9, 1),
            status=FDRStatus.UNDER_REVIEW,
            verification_status=VerificationStatus.PENDING,
            review_priority_score=95,
            review_priority_reasons=[
                "Potential duplicate candidate with FDR-2026-0003",
            ],
            has_potential_duplicate=True,
            compliance_reference="SEC-DEP-PHY-2024",
            notes="Physics Dept deposit submission.",
            submitted_by=user_admin.id,
            assigned_reviewer_id=user_reviewer.id,
        )
        session.add_all([fdr_c1, fdr_c2])
        await session.flush()

        dup_c = DuplicateCandidate(
            fdr_instrument_a_id=fdr_c1.id,
            fdr_instrument_b_id=fdr_c2.id,
            match_score=0.96,
            match_reasons=[
                "Identical FDR number 'ICICI-88239011'",
                "Same issuing bank and deposit amount (₹30,00,000.00)",
                "Identical maturity dates",
            ],
            matching_fields={
                "fdr_number": "ICICI-88239011",
                "bank_name": "ICICI Bank",
                "deposit_amount": "3000000.00",
                "maturity_date": "2027-09-01",
            },
            differing_fields={
                "institution_id": f"{inst2.name} vs {inst3.name}",
                "internal_reference": "FDR-2026-0003 vs FDR-2026-0004",
            },
            file_hash_match=True,
            status=DuplicateStatus.PENDING,
            review_notes="Automated duplicate candidate generated upon submission of FDR-2026-0004.",
        )
        session.add(dup_c)

        # SCENARIO D: Upcoming Maturity (Maturing in 20 days)
        fdr_d = FDRInstrument(
            id=uuid.uuid4(),
            institution_id=inst1.id,
            internal_reference="FDR-2026-0005",
            application_number="APP-NIT-2023-019",
            bank_name="Punjab National Bank",
            branch_name="Civil Lines Branch",
            fdr_number="PNB-44019238",
            deposit_amount=Decimal("1500000.00"),
            currency="INR",
            issue_date=today - timedelta(days=345),
            maturity_date=today + timedelta(days=20),  # Maturing in 20 days!
            status=FDRStatus.ACTIVE,
            verification_status=VerificationStatus.VERIFIED,
            review_priority_score=70,
            review_priority_reasons=["Maturity deadline within 30 days. Renewal or release action required."],
            has_potential_duplicate=False,
            compliance_reference="SEC-DEP-CIVIL-2023",
            notes="Civil Engineering initial endowment deposit.",
            submitted_by=user_inst1.id,
            assigned_reviewer_id=user_reviewer.id,
        )
        session.add(fdr_d)
        await session.flush()

        # SCENARIO E: Renewal In Progress
        fdr_e_parent = FDRInstrument(
            id=uuid.uuid4(),
            institution_id=inst2.id,
            internal_reference="FDR-2026-0006",
            application_number="APP-DEC-2021-005",
            bank_name="Axis Bank",
            branch_name="MG Road Branch",
            fdr_number="AXIS-55214099",
            deposit_amount=Decimal("4000000.00"),
            currency="INR",
            issue_date=today - timedelta(days=1095),
            maturity_date=today - timedelta(days=5),  # Matured 5 days ago
            status=FDRStatus.RENEWAL_PENDING,
            verification_status=VerificationStatus.VERIFIED,
            review_priority_score=60,
            review_priority_reasons=["Parent instrument matured; renewal processing."],
            has_potential_duplicate=False,
            compliance_reference="SEC-DEP-EEE-2021",
            notes="Original Electrical Engineering endowment.",
            submitted_by=user_inst2.id,
        )
        fdr_e_child = FDRInstrument(
            id=uuid.uuid4(),
            institution_id=inst2.id,
            internal_reference="FDR-2026-0007",
            application_number="APP-DEC-2026-REN",
            bank_name="Axis Bank",
            branch_name="MG Road Branch",
            fdr_number="AXIS-55214100",  # New renewed certificate
            deposit_amount=Decimal("4000000.00"),
            currency="INR",
            issue_date=today - timedelta(days=5),
            maturity_date=today + timedelta(days=1090),
            status=FDRStatus.SUBMITTED,
            verification_status=VerificationStatus.PENDING,
            review_priority_score=25,
            review_priority_reasons=["Renewal instrument submitted for verification."],
            has_potential_duplicate=False,
            compliance_reference="SEC-DEP-EEE-2026",
            notes="Renewal deposit certificate replacing AXIS-55214099.",
            submitted_by=user_inst2.id,
            assigned_reviewer_id=user_reviewer.id,
        )
        session.add_all([fdr_e_parent, fdr_e_child])
        await session.flush()

        lifecycle_e = LifecycleRelationship(
            parent_fdr_id=fdr_e_parent.id,
            child_fdr_id=fdr_e_child.id,
            relationship_type=LifecycleRelationshipType.RENEWAL,
            notes="3-Year term extension with Axis Bank roll-over receipt.",
            created_by=user_inst2.id,
        )
        session.add(lifecycle_e)

        renewal_req_e = RenewalRequest(
            original_fdr_id=fdr_e_parent.id,
            new_fdr_id=fdr_e_child.id,
            status=RenewalStatus.PENDING,
            requested_by=user_inst2.id,
            review_notes="Institution submitted updated receipt; pending reviewer validation.",
        )
        session.add(renewal_req_e)

        # SCENARIO F: FDR Release Request Submitted (Autonomous/Closure)
        fdr_f = FDRInstrument(
            id=uuid.uuid4(),
            institution_id=inst3.id,
            internal_reference="FDR-2026-0008",
            application_number="APP-SUS-2021-001",
            bank_name="Canara Bank",
            branch_name="Secretariat Road Branch",
            fdr_number="CANARA-11902345",
            deposit_amount=Decimal("10000000.00"),  # 1 Crore INR
            currency="INR",
            issue_date=date(2021, 3, 1),
            maturity_date=date(2026, 3, 1),
            status=FDRStatus.UNDER_REVIEW,
            verification_status=VerificationStatus.VERIFIED,
            review_priority_score=45,
            review_priority_reasons=["Release request under compliance evaluation."],
            has_potential_duplicate=False,
            compliance_reference="SEC-DEP-UNIV-2021",
            notes="Institutional endowment deposit completed 5-year lock-in.",
            submitted_by=user_admin.id,
            assigned_reviewer_id=user_reviewer.id,
        )
        session.add(fdr_f)
        await session.flush()

        release_req_f = ReleaseRequest(
            fdr_instrument_id=fdr_f.id,
            reason="Mandatory 5-year lock-in completed. Institution granted autonomous degree-awarding status by UGC.",
            supporting_documents=[
                {"title": "UGC Autonomous Notification", "file": "ugc_autonomous_letter.pdf"},
                {"title": "No Dues & Compliance Audit Report", "file": "compliance_audit_2026.pdf"},
            ],
            status=ReleaseStatus.PENDING,
            requested_by=user_admin.id,
            reviewer_notes="Verified autonomous status gazette notification. Forwarded to Approving Authority.",
        )
        session.add(release_req_f)

        # Add an already Released FDR to populate released metrics
        fdr_released = FDRInstrument(
            id=uuid.uuid4(),
            institution_id=inst2.id,
            internal_reference="FDR-2026-0009",
            application_number="APP-DEC-2020-002",
            bank_name="Bank of Baroda",
            branch_name="Indiranagar Branch",
            fdr_number="BOB-99001122",
            deposit_amount=Decimal("2000000.00"),
            currency="INR",
            issue_date=date(2020, 5, 10),
            maturity_date=date(2025, 5, 10),
            status=FDRStatus.RELEASED,
            verification_status=VerificationStatus.VERIFIED,
            review_priority_score=0,
            has_potential_duplicate=False,
            notes="Program closure completed; security deposit returned.",
            submitted_by=user_inst2.id,
        )
        session.add(fdr_released)
        await session.flush()

        release_completed = ReleaseRequest(
            fdr_instrument_id=fdr_released.id,
            reason="Course discontinued with regulatory approval.",
            supporting_documents=[{"title": "NOC Certificate", "file": "noc_closure.pdf"}],
            status=ReleaseStatus.APPROVED,
            requested_by=user_inst2.id,
            reviewed_by=user_reviewer.id,
            reviewer_notes="NOC checked and approved.",
            approved_by=user_approver.id,
            approver_notes="Approved for release by Approving Authority.",
            decision_date=datetime.utcnow() - timedelta(days=30),
        )
        session.add(release_completed)
        await session.flush()
        print("[OK] FDR scenarios A-F created.")

        # -------------------------------------------------------------
        # 4. Create Sample Notifications
        # -------------------------------------------------------------
        print("Creating sample notifications...")
        notif1 = Notification(
            user_id=user_inst1.id,
            title="Maturity Reminder: PNB-44019238",
            message=f"FDR instrument PNB-44019238 is set to mature on {fdr_d.maturity_date.strftime('%d %b %Y')}. Please submit renewal or release papers.",
            notification_type=NotificationType.MATURITY_REMINDER,
            entity_type="fdr_instrument",
            entity_id=fdr_d.id,
            is_read=False,
            due_date=datetime.combine(fdr_d.maturity_date, datetime.min.time()),
        )
        notif2 = Notification(
            user_id=user_inst1.id,
            title="Correction Requested: FDR-2026-0002",
            message="Discrepancy detected in deposit amount. Please submit updated documents.",
            notification_type=NotificationType.CORRECTION_REQUESTED,
            entity_type="fdr_instrument",
            entity_id=fdr_b.id,
            is_read=False,
        )
        notif3 = Notification(
            user_id=user_reviewer.id,
            title="High Priority: Potential Duplicate Flagged",
            message="Instrument ICICI-88239011 appears in multiple submissions across different institutions.",
            notification_type=NotificationType.DUPLICATE_FOUND,
            entity_type="duplicate_candidate",
            entity_id=dup_c.id,
            is_read=False,
        )
        notif4 = Notification(
            user_id=user_approver.id,
            title="Release Request Awaiting Approval",
            message="Canara Bank Rs. 1 Crore endowment release request for Sample University of Science submitted for decision.",
            notification_type=NotificationType.REVIEW_NEEDED,
            entity_type="release_request",
            entity_id=release_req_f.id,
            is_read=False,
        )
        session.add_all([notif1, notif2, notif3, notif4])
        print("[OK] Sample notifications created.")

        # -------------------------------------------------------------
        # 5. Create Audit Events
        # -------------------------------------------------------------
        print("Creating audit events...")
        audit1 = AuditEvent(
            user_id=user_inst1.id,
            role="institution_user",
            action="FDR_SUBMITTED",
            entity_type="FDRInstrument",
            entity_id=fdr_a.id,
            timestamp=datetime.utcnow() - timedelta(days=12),
            after_values={"internal_reference": "FDR-2026-0001", "deposit_amount": 5000000.0},
            reason="Initial submission of security deposit",
            correlation_id=str(uuid.uuid4()),
        )
        audit2 = AuditEvent(
            user_id=user_reviewer.id,
            role="reviewer",
            action="VERIFICATION_COMPLETED",
            entity_type="FDRInstrument",
            entity_id=fdr_a.id,
            timestamp=datetime.utcnow() - timedelta(days=10),
            before_values={"status": "UNDER_REVIEW"},
            after_values={"status": "VERIFIED"},
            reason="All document and bank checks passed successfully",
            correlation_id=str(uuid.uuid4()),
        )
        audit3 = AuditEvent(
            user_id=user_reviewer.id,
            role="reviewer",
            action="CORRECTION_REQUESTED",
            entity_type="FDRInstrument",
            entity_id=fdr_b.id,
            timestamp=datetime.utcnow() - timedelta(days=2),
            before_values={"status": "UNDER_REVIEW"},
            after_values={"status": "CORRECTION_REQUESTED"},
            reason="Deposit amount mismatch of Rs. 5,00,000 found during extraction check",
            correlation_id=str(uuid.uuid4()),
        )
        audit4 = AuditEvent(
            user_id=None,
            role="system",
            action="DUPLICATE_CANDIDATE_FLAGGED",
            entity_type="DuplicateCandidate",
            entity_id=dup_c.id,
            timestamp=datetime.utcnow() - timedelta(days=1),
            after_values={"match_score": 0.96, "matched_fdr": "ICICI-88239011"},
            reason="Duplicate instrument match detected across institutions",
            correlation_id=str(uuid.uuid4()),
        )
        audit5 = AuditEvent(
            user_id=user_admin.id,
            role="admin",
            action="RELEASE_REQUEST_SUBMITTED",
            entity_type="ReleaseRequest",
            entity_id=release_req_f.id,
            timestamp=datetime.utcnow() - timedelta(hours=6),
            after_values={"amount": 10000000.0, "reason": "UGC Autonomous status grant"},
            reason="Autonomous degree-awarding status granted",
            correlation_id=str(uuid.uuid4()),
        )
        session.add_all([audit1, audit2, audit3, audit4, audit5])

        # -------------------------------------------------------------
        # 6. Create System Configuration
        # -------------------------------------------------------------
        print("Creating system configuration...")
        sys_config1 = SystemConfiguration(
            key="compliance.minimum_deposit_amount",
            value={"amount": 1000000, "currency": "INR"},
            description="Minimum deposit amount required for standard program accreditation.",
            updated_by=user_admin.id,
        )
        sys_config2 = SystemConfiguration(
            key="compliance.maturity_reminder_schedule_days",
            value={"schedule": [60, 30, 15, 7, 0]},
            description="Days before maturity to generate automated compliance reminder notifications.",
            updated_by=user_admin.id,
        )
        sys_config3 = SystemConfiguration(
            key="ai.extraction_confidence_threshold",
            value={"minimum_confidence": 0.85, "auto_validate": True},
            description="Threshold for automated acceptance of extracted fields.",
            updated_by=user_admin.id,
        )
        session.add_all([sys_config1, sys_config2, sys_config3])

        await session.commit()
        print("[OK] All data successfully committed to database.")

    # -------------------------------------------------------------
    # 7. Print summary
    # -------------------------------------------------------------
    print("\n" + "=" * 60)
    print("       FDR Intelligence & Compliance Portal Seed Summary")
    print("=" * 60)
    print("Institutions created:")
    print("  1. INST-001: National Institute of Technology - Demo")
    print("  2. INST-002: Demo Engineering College")
    print("  3. INST-003: Sample University of Science")
    print("\nUser Accounts (Password: as specified):")
    print("  * admin@fdrportal.demo     / Admin@123      (Role: admin)")
    print("  * reviewer@fdrportal.demo  / Reviewer@123   (Role: reviewer)")
    print("  * approver@fdrportal.demo  / Approver@123   (Role: approving_authority)")
    print("  * inst1@fdrportal.demo     / Institute1@123 (Role: institution_user - INST-001)")
    print("  * inst2@fdrportal.demo     / Institute2@123 (Role: institution_user - INST-002)")
    print("\nScenarios Loaded:")
    print("  * Scenario A: Verified Active FDR (SBI - Rs. 50L)")
    print("  * Scenario B: Discrepancy / Correction Requested (HDFC - Rs. 25L vs Rs. 20L)")
    print("  * Scenario C: Duplicate Detection Flag (ICICI - Rs. 30L matched across 2 inst)")
    print("  * Scenario D: Upcoming Maturity in 20 days (PNB - Rs. 15L)")
    print("  * Scenario E: Renewal in progress (Axis - Rs. 40L old -> new)")
    print("  * Scenario F: Release Request pending approver decision (Canara - Rs. 1 Cr)")
    print("=" * 60)
    print("Database seeding completed successfully!")


if __name__ == "__main__":
    asyncio.run(seed_database())
