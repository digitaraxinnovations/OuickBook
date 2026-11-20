from app.core.exceptions import AuthenticationError, ConflictError
from app.core.security import PasswordHasher, TokenService
from app.models import CompanyMember, User
from app.models.enums import UserRole
from app.repositories.company_repository import UserRepository
from app.schemas.auth import LoginRequest, SignupRequest
from app.services.base import BaseService
from app.services.company_service import CompanyService
from app.services.integration_service import API_KEY_PREFIX, IntegrationService


class AuthService(BaseService):
    def __init__(
        self,
        session,
        user_repository: UserRepository,
        company_service: CompanyService,
        password_hasher: PasswordHasher,
        token_service: TokenService,
    ):
        super().__init__(session)
        self.user_repository = user_repository
        self.company_service = company_service
        self.password_hasher = password_hasher
        self.token_service = token_service

    def signup(self, data: SignupRequest) -> str:
        """Create a company and its first user. Returns a login token."""
        email = data.email.lower()
        if self.user_repository.get_by_email(email) is not None:
            raise ConflictError("An account with this email already exists.")

        company = self.company_service.create_with_default_accounts(data.company_name)
        user = User(
            company_id=company.id,
            email=email,
            full_name=data.full_name,
            password_hash=self.password_hasher.hash(data.password),
        )
        self.user_repository.add(user)
        self.session.add(CompanyMember(company_id=company.id, user_id=user.id, role=UserRole.ADMIN, is_primary_admin=True, is_active=True))
        self.commit()
        return self.token_service.create_access_token(user.id)

    def login(self, data: LoginRequest) -> str:
        user = self.user_repository.get_by_email(data.email.lower())
        if user is None or not self.password_hasher.verify(data.password, user.password_hash):
            raise AuthenticationError("Incorrect email or password.")
        if not user.is_active:
            raise AuthenticationError("This user has been deactivated.")
        return self.token_service.create_access_token(user.id)

    def get_user_from_token(self, token: str) -> User:
        if token.startswith(API_KEY_PREFIX):
            return IntegrationService(self.session).user_for_key(token)
        user_id = self.token_service.read_user_id(token)
        user = self.user_repository.get(user_id)
        if user is None or not user.is_active:
            raise AuthenticationError("Your session is invalid. Please sign in again.")
        return user
