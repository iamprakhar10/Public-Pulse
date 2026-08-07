from sqlalchemy import (Boolean, 
                        Integer, 
                        String,
                        DateTime, 
                        func, 
                        ForeignKey, 
                        Text,
                        Enum as SQLAlchemyEnum,
                        UniqueConstraint,
                        
                        )

from app.constants.complaint import (
    ComplaintCategory,
    ComplaintStatus,
    MessageRole,
)

from sqlalchemy.orm import Mapped, mapped_column, relationship

from datetime import datetime

from app.database.base import Base


"""print(type(mapped_column))
print("---")
print(type(Mapped))
print(Mapped)"""

class User(Base):
    __tablename__ = 'users'

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    email: Mapped[str] = mapped_column(String(255), nullable=False, unique=True)
    phone: Mapped[str] = mapped_column(String(20), unique=True, nullable=False)
    is_verified: Mapped[bool] = mapped_column(Boolean, default=False)
    hashed_password: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
    )
    created_at: Mapped[datetime] = mapped_column(
    DateTime(timezone=True),
    server_default=func.now(),
    )
    complaints: Mapped[list['Complaint']] = relationship(
        back_populates='user',
        cascade='all, delete-orphan',
    )
    gmail_credential: Mapped["GmailCredential | None"] = relationship(
        back_populates='user',
        cascade="all, delete-orphan",
        uselist=False, #on user can have 0 or 1 GmailCredential
        single_parent=True,
    )

# One User → Many Complaints
# Deleting a user will also delete their 
# complaint records through the ORM relationship
























class GmailCredential(Base):
    """
    Stoes one user's GmailOAuth authorization

    No password will be stored

    We will store refresh token(which will be encrypted)
    Later it can be decrypted and exchanged for a short lived Google access token

    """

    __tablename__ = "gmail_credentials"

    id: Mapped[int] = mapped_column(
        primary_key=True,
        index=True,
    )

    # One public pulse user can only have one connected gmail account
    user_id: Mapped[int] = mapped_column(
        ForeignKey(
            "users.id",
            ondelete='CASCADE',
        ),
        nullable=False,
        unique=True,
        index=True,
    )

    # Google's stable identifier for the connected Google account.
    # 
    # This is better than relying only on email address because 
    # an email id can theoritically change 
    google_account_id: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        unique=True,
        index=True,
    )

    # Useful for displaying:
    # "Cnnected as example@gmail.com" 
    google_email: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
    )

    # This contains encrypted text, we will never store plain refresh
    # token 
    encrypted_refresh_token: Mapped[str] = mapped_column(
        Text,
        nullable=False,
    )

    # Permission granted by the user
    # like -> https://www.googleapi.com/auth/gmail.send
    scopes: Mapped[str] = mapped_column(
        Text,
        nullable=False,
    ) 

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    user: Mapped["User"] = relationship(
        back_populates="gmail_credential",
    )




















class GmailOAuthState(Base):
    """
    This stores a temporary Google OAuth state value

    A state value will link google callback to the Public pulse
    user who started the Gmail connection

    Only a SHA-256 hash of the state is stored. The original random
    state value travels through the browser.
    """

    __tablename__ = "gmail_oauth_states"

    id: Mapped[int] = mapped_column(
        primary_key=True,
        index=True,
    )

    user_id: Mapped[int] = mapped_column(
        ForeignKey(
            "users.id",
            ondelete='CASCADE',
        ),
        nullable=False,
        index=True,
    )

    # Storing the hash instead of the actual browser-facing state 
    # value 
    state_hash : Mapped[str] = mapped_column(
        String(64),
        nullable=False,
        unique=True,
        index=True,
    )

    code_verifier: Mapped[str] = mapped_column(
        String(128),
        nullable=False,
    )

    # State should remain valid only for a short period
    expires_at : Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
    )

    # Once the callback consumes the state, it can't be reused
    used_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

















class Complaint(Base):
    """
    Represents one complete civic complaint case.

    This table stores the latest structured information extracted
    from the conversation.

    This is not the whole complaint, user can go back and forth
    with the llm, we will assign the WHOLE complaint a id number.

    Every conversation will get added into database with a column
    = id which will be the same for a WHOLE complaint
    
    """

    __tablename__='complaints'

    id: Mapped[int] = mapped_column(
        primary_key=True,
        index=True,
    )

    #The authenticated user who owns this complaint
    user_id: Mapped[int] = mapped_column(
        ForeignKey('users.id', ondelete='CASCADE'),
        nullable= False,
        index=True,
    )

    # Short structured summary produced from the conversation
    summary: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    # Standard category selected from ComplaintCategory
    #
    # It can initially be nullable because LLM may not know the
    # category from the user's first message.

    category: Mapped[ComplaintCategory | None] = mapped_column(
        SQLAlchemyEnum(
            ComplaintCategory, 
            name='complaint_category',
            native_enum = False,
            create_constraint=True,
            validate_strings=True,
            values_callable=lambda enum_class: [
                item.value for item in enum_class
            ],

        ),
        nullable=True,
        index=True,
    )
#     Mapped[int | None]
#     → Python typing

# nullable=False
#     → database constraint

    # City where the civic problem occurred
    city: Mapped[str | None] = mapped_column(
        String(100),
        nullable=True,
        index= True,
    )

    #new canonical city reference
    city_id: Mapped[int | None] = mapped_column(
        ForeignKey('cities.id'),
        nullable=True,
    )

    # Gives access to the related City ORM object:
    # complaint.city_record.name
    city_record: Mapped['City | None'] = relationship()

    # Locality or Neighbourhood where the problem exists.
    area: Mapped[str | None] = mapped_column(
        String(150),
        nullable=True,
    )

    # Six digit pincode used for authority matching
    # and used when we eill make dashboard
    pincode: Mapped[str | None] = mapped_column(
        String(6),
        nullable=True,
        index=True
    )

    authority_id: Mapped[int | None] = mapped_column(
        ForeignKey("authorities.id", ondelete='SET NULL'),
        nullable=True,
        index=True,
    )

    authority: Mapped["Authority | None"] = relationship(
        back_populates="complaints",
    )

    # Current stage of complaint
    status: Mapped[ComplaintStatus] = mapped_column(
        SQLAlchemyEnum(
            ComplaintStatus,
            name='complaint_status',
            native_enum=False,
            create_constraint=True,
            validate_strings=True,
            values_callable=lambda enum_class: [
                item.value for item in enum_class
            ],
        ),
        default=ComplaintStatus.DRAFT,
        nullable=False,
        index=True,
    )

    # Formal email subject generated after enough information
    #has been collected
    email_subject: Mapped[str|None] = mapped_column(
        String(255),
        nullable=True,
    )

    # Formal email complaint generated by the LLM
    email_body: Mapped[str|None] = mapped_column(
        Text,
        nullable=True,
    )

    # Time when firstcomplaint was created
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    # Time when any complaint information was last updated.
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    # Connects this complaint to the user who has made this 
    # complaint
    user: Mapped['User'] = relationship(
        back_populates='complaints',
    )

    # Contains every user AND AI-assistant message belonging
    #to this complaint conversation.

    messages: Mapped[list['ComplaintMessage']] = relationship(
        back_populates='complaint',
        cascade='all, delete-orphan',
        order_by='ComplaintMessage.created_at'
    )












class ComplaintMessage(Base):
    """
    Stores on individual message in a complaint conversation.

    Every user message and every AI-assistant message becomes a
    separate row in this this tAbLe.
    """

    __tablename__ = 'complaint_messages'

    #Unique identifier for this message.
    id: Mapped[int] = mapped_column(
        primary_key=True,
        index=True,
    )

    # The complaint conversation to which this message belongs to
    complaint_id : Mapped[int] = mapped_column(
        ForeignKey(
            'complaints.id',
            ondelete='CASCADE',
        ),
        nullable=False,
        index=True,
    )

    # Identifies whether this message came from a user or AI-Assistant
    role: Mapped[MessageRole] = mapped_column(
        SQLAlchemyEnum(MessageRole,
                        name='complaint_messag_role',
                        native_enum=False,
                        create_constraint=True,
                        values_callable=lambda enum_class: [
                            item.value for item in enum_class
                        ],
                       ),
                    nullable=False
    )

    #Complete text of this individual message.
    content: Mapped[str] = mapped_column(
        Text,
        nullable=False,
    )

    # Time when the message was stored.
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    #Connects this message back to its parent complaint.
    complaint: Mapped['Complaint'] = relationship(
        back_populates='messages',
    )
      










class State(Base):
    """
    Indian states supported by publicpulse

    Other tables should refer to a state through it's numeric Id
    """
    __tablename__= 'states'

    id: Mapped[int] = mapped_column(
        primary_key=True,
    )

    name: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
        unique=True,
    )

    code: Mapped[str] = mapped_column(
        String(10),
        nullable=False,
        unique=True,
    )

    # One state can contain multiple cities
    cities: Mapped[list['City']] = relationship(
        back_populates='state',
    )



# State.cities = relationship(back_populates="state")
# City.state = relationship(back_populates="cities")


class City(Base):
    """
    Canonical city record.

    Example:
        id = 1
        name = "Jabalpur"
        normalized_name = "jabalpur"
        state_id = 1

    Complaints and authorities will eventually reference city.id.
    """
    __tablename__= 'cities'

    id: Mapped[int] = mapped_column(
        primary_key=True,
    )

    #Display name of cities for users
    name: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
    )

    # Cleaned version used for lookup.
    #
    # Example:
    # "Jabalpur" -> "jabalpur"
    normalized_name: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
    )

    state_id: Mapped[int] = mapped_column(
        ForeignKey('states.id'),
        nullable=False,
    )
    # Lets us disable a city without deleting its records.
    is_supported: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=True,
    )

    state: Mapped["State"] = relationship(
        back_populates="cities",
    )

    aliases: Mapped[list["CityAlias"]] = relationship(
        back_populates="city",
        cascade="all, delete-orphan",
    )

    authorities : Mapped[list['Authority']] = relationship(
        back_populates='city',
        cascade='all, delete-orphan',
    )

    

    __table_args__ = (
        # Two cities in the same state cannot have the same
        # normalized canonical name.
        UniqueConstraint(
            "normalized_name",
            "state_id",
            name="uq_city_normalized_name_state",
        ),
    )









class CityAlias(Base):
    """
    Another/similar name that resolves to a canonical city

    Examples:
        "jbp" -> Jabalpur
        "jubbulpore" -> Jabalpur
        "lko" -> Lucknow
    """

    __tablename__= 'city_aliases'

    id: Mapped[int] = mapped_column(
        primary_key=True,
    )

    #Human-radable alias
    alias: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
    )

    # Normalized alias used during matching.
    normalized_alias: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
    )

    city_id: Mapped[int] = mapped_column(
        ForeignKey("cities.id"),
        nullable=False,
    )

    city: Mapped["City"] = relationship(
        back_populates="aliases",
    )

    __table_args__ = (
        # For the first version, an alias must point to only one city.
        # This prevents "jbp" from accidentally pointing to multiple cities.
        UniqueConstraint(
            "normalized_alias",
            name="uq_city_alias_normalized",
        ),
    )





class Authority(Base):
    """
    Government authorities to whom we will send the email/complaint
    """

    __tablename__= "authorities"

    id: Mapped[int] = mapped_column(primary_key=True)

    name: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
    )

    department: Mapped[str] =  mapped_column(
        String(255),
        nullable=False,
    )

    category: Mapped[ComplaintCategory] = mapped_column(
        SQLAlchemyEnum(
            ComplaintCategory,
            name='authority_complaint_category',
            native_enum=False,
            create_constraint=True,
            validate_strings=True,
            values_callable=lambda enum_class: [
                item.value for item in enum_class
            ],
        ),
        nullable=False,
        index=True,
    )

    city_id: Mapped[int] = mapped_column(
        ForeignKey(
            'cities.id',
            ondelete='CASCADE',
            ),
            nullable=False,
            index=True,
    )

    pincode: Mapped[str] = mapped_column(
        String(6),
        nullable=False,
        index=True,
    )

    email: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
    )

    is_active: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=True,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    city: Mapped['City'] = relationship(
        back_populates='authorities',
    )

    complaints : Mapped[list["Complaint"]] = relationship(
        back_populates='authority',
    )

    __table_args__ = (
        UniqueConstraint(
            "city_id",
            "pincode",
            "category",
            name="uq_authority_city_pincode_category",
        ),
    )

    