"""
Companies a user can work in, the users of a company, and invitations.

- A user is a member of one or more companies, with a role in each.
- `User.company_id` is the company they are working in now; switching
  companies changes it (only to a company they are a member of).
- Admins invite people by email. The invite link lets them create an
  account (or use their existing one) and join with the chosen role.
"""

import secrets
from datetime import datetime, timedelta, timezone

from sqlalchemy import select

from app.core.config import Settings
from app.core.exceptions import AuthenticationError, BusinessRuleError, ConflictError, NotFoundError, PermissionDeniedError
from app.core.permissions import ROLE_LABELS, area_of, is_allowed
from app.core.security import PasswordHasher, TokenService
from app.integrations.email import OutgoingEmail
from app.models import Company, CompanyMember, Invitation, User
from app.models.enums import UserRole
from app.repositories.company_repository import CompanyRepository, UserRepository
from app.schemas.platform import (
    AcceptInvitation,
    CompanyMembership,
    InvitationCreate,
    InvitationInfo,
    MemberRead,
    MemberUpdate,
    RoleInfo,
)
from app.services.base import BaseService
from app.services.company_service import CompanyService
from app.services.email_service import EmailService

INVITATION_DAYS = 14


class MembershipService(BaseService):
    def __init__(
        self,
        session,
        settings: Settings,
        user_repository: UserRepository,
        company_repository: CompanyRepository,
        company_service: CompanyService,
        email_service: EmailService,
        password_hasher: PasswordHasher,
        token_service: TokenService,
    ):
        super().__init__(session)
        self.settings = settings
        self.user_repository = user_repository
        self.company_repository = company_repository
        self.company_service = company_service
        self.email_service = email_service
        self.password_hasher = password_hasher
        self.token_service = token_service

    # ---------- membership lookups ----------

    def member(self, company_id: int, user_id: int) -> CompanyMember | None:
        query = select(CompanyMember).where(CompanyMember.company_id == company_id, CompanyMember.user_id == user_id)
        return self.session.scalar(query)

    def memberships_of(self, user_id: int) -> list[CompanyMember]:
        query = select(CompanyMember).where(CompanyMember.user_id == user_id, CompanyMember.is_active.is_(True))
        return list(self.session.scalars(query.order_by(CompanyMember.id)))

    def check_access(self, user: User, path: str, method: str) -> CompanyMember:
        """The user's role in their current company, if it allows this request."""
        member = self.member(user.company_id, user.id)
        if member is None or not member.is_active:
            # Lost access to the current company: move to another one they still have.
            others = self.memberships_of(user.id)
            if not others:
                raise AuthenticationError("You no longer have access to any company.")
            user.company_id = others[0].company_id
            self.commit()
            member = others[0]
        if not is_allowed(member.role, area_of(path, self.settings.api_prefix), method):
            raise PermissionDeniedError("Your role does not allow this. Ask an admin for access.")
        return member

    # ---------- companies ----------

    def companies(self, user: User) -> list[CompanyMembership]:
        result = []
        for member in self.memberships_of(user.id):
            company = self.company_repository.get(member.company_id)
            result.append(
                CompanyMembership(company_id=company.id, company_name=company.name, role=member.role, is_current=company.id == user.company_id)
            )
        return result

    def create_company(self, user: User, name: str) -> Company:
        company = self.company_service.create_with_default_accounts(name)
        self.session.add(CompanyMember(company_id=company.id, user_id=user.id, role=UserRole.ADMIN, is_primary_admin=True, is_active=True))
        user.company_id = company.id
        self.commit()
        return company

    def switch_company(self, user: User, company_id: int) -> None:
        member = self.member(company_id, user.id)
        if member is None or not member.is_active:
            raise NotFoundError("You are not a member of that company.")
        user.company_id = company_id
        self.commit()

    # ---------- users of a company ----------

    def roles(self) -> list[RoleInfo]:
        return [RoleInfo(role=role, label=label) for role, label in ROLE_LABELS.items()]

    def members(self, company_id: int) -> list[MemberRead]:
        query = select(CompanyMember).where(CompanyMember.company_id == company_id).order_by(CompanyMember.id)
        result = []
        for member in self.session.scalars(query):
            result.append(
                MemberRead(
                    user_id=member.user_id,
                    full_name=member.user.full_name,
                    email=member.user.email,
                    role=member.role,
                    is_primary_admin=member.is_primary_admin,
                    is_active=member.is_active,
                )
            )
        return result

    def update_member(self, company_id: int, user_id: int, data: MemberUpdate) -> list[MemberRead]:
        member = self.member(company_id, user_id)
        if member is None:
            raise NotFoundError("That user is not in this company.")
        if member.is_primary_admin and (data.role != UserRole.ADMIN or not data.is_active):
            raise BusinessRuleError("The primary admin always keeps full access.")
        member.role = data.role
        member.is_active = data.is_active
        self.commit()
        return self.members(company_id)

    # ---------- invitations ----------

    def invitations(self, company_id: int) -> list[Invitation]:
        query = select(Invitation).where(Invitation.company_id == company_id, Invitation.accepted_at.is_(None))
        return list(self.session.scalars(query.order_by(Invitation.id.desc())))

    def invite(self, company_id: int, inviter: User, data: InvitationCreate) -> Invitation:
        email = data.email.lower()
        existing_user = self.user_repository.get_by_email(email)
        if existing_user is not None and self.member(company_id, existing_user.id) is not None:
            raise ConflictError("That person is already a user of this company.")
        invitation = Invitation(
            company_id=company_id,
            email=email,
            role=data.role,
            token=secrets.token_urlsafe(32),
            invited_by_user_id=inviter.id,
            expires_at=datetime.now(timezone.utc) + timedelta(days=INVITATION_DAYS),
        )
        self.session.add(invitation)
        self.session.flush()

        company = self.company_repository.get(company_id)
        link = f"{self.settings.public_app_url}/accept-invite?token={invitation.token}"
        body = (
            f"{inviter.full_name} invited you to {company.name} on Ledgerly "
            f"({ROLE_LABELS[data.role]}).\n\nAccept the invitation: {link}\n\n"
            f"The link works for {INVITATION_DAYS} days."
        )
        self.email_service.send(
            company_id, OutgoingEmail(to=email, subject=f"Join {company.name} on Ledgerly", body=body), "INVITATION", invitation.id
        )
        self.commit()
        return invitation

    def cancel_invitation(self, company_id: int, invitation_id: int) -> None:
        invitation = self.session.get(Invitation, invitation_id)
        if invitation is None or invitation.company_id != company_id or invitation.accepted_at is not None:
            raise NotFoundError("Invitation not found.")
        self.session.delete(invitation)
        self.commit()

    def find_invitation(self, token: str) -> Invitation:
        invitation = self.session.scalar(select(Invitation).where(Invitation.token == token))
        if invitation is None or invitation.accepted_at is not None:
            raise NotFoundError("This invitation link is not valid any more.")
        if invitation.expires_at < datetime.now(timezone.utc):
            raise BusinessRuleError("This invitation has expired. Ask for a new one.")
        return invitation

    def invitation_info(self, token: str) -> InvitationInfo:
        invitation = self.find_invitation(token)
        company = self.company_repository.get(invitation.company_id)
        has_account = self.user_repository.get_by_email(invitation.email) is not None
        return InvitationInfo(company_name=company.name, email=invitation.email, role=invitation.role, has_account=has_account)

    def accept(self, token: str, data: AcceptInvitation) -> str:
        """Join the company. Returns a login token."""
        invitation = self.find_invitation(token)
        user = self.user_repository.get_by_email(invitation.email)
        if user is None:
            if not data.full_name:
                raise BusinessRuleError("Enter your name to create your account.")
            user = User(
                company_id=invitation.company_id,
                email=invitation.email,
                full_name=data.full_name,
                password_hash=self.password_hasher.hash(data.password),
            )
            self.user_repository.add(user)
        elif not self.password_hasher.verify(data.password, user.password_hash):
            raise AuthenticationError("Incorrect password for your existing account.")

        if self.member(invitation.company_id, user.id) is None:
            self.session.add(CompanyMember(company_id=invitation.company_id, user_id=user.id, role=invitation.role, is_active=True))
        user.company_id = invitation.company_id
        invitation.accepted_at = datetime.now(timezone.utc)
        self.commit()
        return self.token_service.create_access_token(user.id)
