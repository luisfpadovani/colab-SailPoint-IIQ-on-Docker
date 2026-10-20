CREATE DATABASE appMock
GO

CREATE LOGIN [appMock] WITH PASSWORD='$(APP_MOCK_PASSWORD)', CHECK_POLICY=ON,
DEFAULT_DATABASE=appMock
GO

USE appMock
GO

CREATE USER appMock FOR LOGIN appMock WITH DEFAULT_SCHEMA =
dbo
GO

-- Permissions granted on procedures after their creation (ownership chaining).

ALTER DATABASE appMock SET ALLOW_SNAPSHOT_ISOLATION ON
GO
ALTER DATABASE appMock SET READ_COMMITTED_SNAPSHOT ON
GO

create table tbl_user (
        iduser int  not null IDENTITY(1,1),
        name nvarchar(200) not null,
        login nvarchar(200) not null UNIQUE,
        password_salt varbinary(32) not null,
        password_hash varbinary(64) not null,
	status tinyint not null,
        primary key (iduser)
);
GO
create index tbl_user_iduser on tbl_user (iduser);
GO

create table tbl_group (
        idgroup int not null IDENTITY(1,1),
        name nvarchar(200) not null,
        description nvarchar(200) not null,
	status tinyint not null,
        primary key (idgroup)
);
GO
create index tbl_group_idgroup on tbl_group (idgroup);
GO

create table tbl_user_group (
        idusergroup int not null IDENTITY(1,1),
        idgroup int not null,
        iduser int not null,
        primary key (idusergroup)
);
GO
create index tbl_user_group_idusergroup on tbl_user_group (idusergroup);
GO


ALTER TABLE tbl_user_group  WITH CHECK ADD  CONSTRAINT [FK_tbl_group] FOREIGN KEY(idgroup)
REFERENCES tbl_group (idgroup)
ON DELETE CASCADE
GO
ALTER TABLE tbl_user_group CHECK CONSTRAINT [FK_tbl_group]
GO


ALTER TABLE tbl_user_group  WITH CHECK ADD  CONSTRAINT [FK_tbl_user] FOREIGN KEY(iduser)
REFERENCES tbl_user (iduser)
ON DELETE CASCADE
GO
ALTER TABLE tbl_user_group CHECK CONSTRAINT [FK_tbl_user]
GO

-- BEGIN GENERATED SAMPLE USERS
INSERT INTO tbl_user([name],[login],[password_salt],[password_hash],[status]) SELECT N'Lisa Lewis','00000001',s.salt,HASHBYTES('SHA2_512',s.salt + CRYPT_GEN_RANDOM(32)),'1' FROM (SELECT CRYPT_GEN_RANDOM(32) AS salt) s;
INSERT INTO tbl_user([name],[login],[password_salt],[password_hash],[status]) SELECT N'Bryan Villarreal','00000002',s.salt,HASHBYTES('SHA2_512',s.salt + CRYPT_GEN_RANDOM(32)),'1' FROM (SELECT CRYPT_GEN_RANDOM(32) AS salt) s;
INSERT INTO tbl_user([name],[login],[password_salt],[password_hash],[status]) SELECT N'Brenda Johnson','00000048',s.salt,HASHBYTES('SHA2_512',s.salt + CRYPT_GEN_RANDOM(32)),'1' FROM (SELECT CRYPT_GEN_RANDOM(32) AS salt) s;
INSERT INTO tbl_user([name],[login],[password_salt],[password_hash],[status]) SELECT N'Deborah Charles','00000066',s.salt,HASHBYTES('SHA2_512',s.salt + CRYPT_GEN_RANDOM(32)),'1' FROM (SELECT CRYPT_GEN_RANDOM(32) AS salt) s;
INSERT INTO tbl_user([name],[login],[password_salt],[password_hash],[status]) SELECT N'Tyler Curtis','00000051',s.salt,HASHBYTES('SHA2_512',s.salt + CRYPT_GEN_RANDOM(32)),'1' FROM (SELECT CRYPT_GEN_RANDOM(32) AS salt) s;
-- END GENERATED SAMPLE USERS


INSERT INTO tbl_group([name],[description],[status]) VALUES('Administrator','System administrator of app mock','1');
INSERT INTO tbl_group([name],[description],[status]) VALUES('Analyst','Analyst of app mock','1');
INSERT INTO tbl_group([name],[description],[status]) VALUES('Audit','Audit of app mock','1');


INSERT INTO tbl_user_group([iduser],[idgroup]) VALUES(1,1);
INSERT INTO tbl_user_group([iduser],[idgroup]) VALUES(1,2);
INSERT INTO tbl_user_group([iduser],[idgroup]) VALUES(1,3);
INSERT INTO tbl_user_group([iduser],[idgroup]) VALUES(2,3);
INSERT INTO tbl_user_group([iduser],[idgroup]) VALUES(3,3);
INSERT INTO tbl_user_group([iduser],[idgroup]) VALUES(4,2);
INSERT INTO tbl_user_group([iduser],[idgroup]) VALUES(5,2);
GO


CREATE PROCEDURE GET_ALL_USER
AS
BEGIN
        SELECT u.name,u.login,u.status, STRING_AGG(g.name, ',')  as profile
                        FROM tbl_user u
                LEFT JOIN
                        tbl_user_group ug
                        ON u.iduser = ug.iduser
                LEFT JOIN
                        tbl_group g
                        ON g.idgroup = ug.idgroup
        Group by u.name,u.login,u.status
END
GO

CREATE PROCEDURE GET_BY_USER
(
        @login nvarchar(200)
)
AS
BEGIN
        SELECT u.name,u.login,u.status, STRING_AGG(g.name, ',')  as profile
                        FROM tbl_user u
                LEFT JOIN
                        tbl_user_group ug
                        ON u.iduser = ug.iduser
                LEFT JOIN
                        tbl_group g
                        ON g.idgroup = ug.idgroup
           where u.login = @login
        Group by u.name,u.login,u.status
END
GO

CREATE PROCEDURE GET_ALL_GROUP
AS
BEGIN
SELECT name,description,status FROM tbl_group
END
GO

CREATE PROCEDURE GET_BY_GROUP
(
        @name nvarchar(200)
)
AS
SELECT name,description,status FROM tbl_group where name = @name
GO

CREATE PROCEDURE [dbo].[INSERT_USER]
(
        @name nvarchar(200),
        @login nvarchar(200),
        @group nvarchar(200)
)
AS
BEGIN

    SET XACT_ABORT ON;
    BEGIN TRY
        BEGIN TRANSACTION;
        IF EXISTS (SELECT 1 FROM tbl_user WITH (UPDLOCK, HOLDLOCK) WHERE login = @login OR name = @name)
            THROW 50001, 'User already exists', 1;
        DECLARE @salt varbinary(32) = CRYPT_GEN_RANDOM(32);
        INSERT INTO tbl_user([name],[password_salt],[password_hash],[login],[status])
        VALUES(@name,@salt,HASHBYTES('SHA2_512',@salt + CRYPT_GEN_RANDOM(32)),@login,1);
        DECLARE @idUser INT = SCOPE_IDENTITY();
        INSERT INTO tbl_user_group (iduser, idgroup)
        SELECT @idUser, idgroup FROM tbl_group WHERE name IN (SELECT value FROM STRING_SPLIT(@group, ','));
        COMMIT;
    END TRY
    BEGIN CATCH
        IF @@TRANCOUNT > 0 ROLLBACK;
        THROW;
    END CATCH;
END
GO

CREATE PROCEDURE INSERT_GROUP
(
        @name nvarchar(200),
        @description nvarchar(200)
)
AS
BEGIN
    IF EXISTS (SELECT 1 FROM tbl_group WHERE name = @name)
    BEGIN
        DECLARE @Message varchar(200)
        set @Message = CONCAT('The existing ', @name, 'group')
        RAISERROR(@Message, 16, 1)
    END
    ELSE
        INSERT INTO tbl_group([name],[description],[status]) VALUES(@name,@description,'1');
END
GO

CREATE PROCEDURE [dbo].[DELETE_USER]
(
        @login nvarchar(200)
)
AS
BEGIN
    DECLARE @idUser INT
    set @idUser = (select idUser from tbl_user where [login] = @login)

    DELETE FROM tbl_user_group where idUser = @idUser;
    DELETE FROM tbl_user where idUser = @idUser;
END
GO

CREATE PROCEDURE [dbo].[DELETE_GROUP]
(
        @name varchar(200)
)
AS
BEGIN
    DECLARE @idGroup INT
    set @idGroup = (select idGroup from tbl_group where [name] = @name)

    DELETE FROM tbl_user_group where idgroup = @idGroup
    DELETE FROM tbl_group where idgroup = @idgroup
END
GO

CREATE PROCEDURE [dbo].[UPDATE_USER]
 (
        @login nvarchar(200),
        @field nvarchar(200),
        @value nvarchar(200),
        @group_add nvarchar(200),
        @group_delete nvarchar(200)
 )
AS
BEGIN
        DECLARE @idUser INT
        set @idUser = (select iduser from tbl_user where [login] = @login)

        IF @field = 'name'
        BEGIN
            Update tbl_user set name = @value where idUser = @idUser
        END


        IF @field = 'status'
        BEGIN
            Update tbl_user set status = @value where idUser = @idUser
        END

        IF @field = 'password'
        BEGIN
            DECLARE @salt varbinary(32) = CRYPT_GEN_RANDOM(32);
            UPDATE tbl_user SET password_salt = @salt, password_hash = HASHBYTES('SHA2_512', @salt + CONVERT(varbinary(max), @value)) WHERE iduser = @idUser
        END

        DELETE tbl_user_group where iduser = @idUser AND idgroup IN(Select idgroup From tbl_group where name IN(Select value from STRING_SPLIT(@group_delete, ',')))

        INSERT INTO tbl_user_group (iduser, idgroup)
        Select @idUser, idgroup from tbl_group where name IN(Select value from STRING_SPLIT(@group_add, ','))
END
GO

CREATE PROCEDURE [dbo].[UPDATE_GROUP]
(
        @name nvarchar(200),
        @field nvarchar(200),
        @value nvarchar(200)
)
AS
BEGIN

        DECLARE @idGroup INT
        set @idGroup = (select idGroup from tbl_group where [name] = @name)

        IF @field = 'description'
        BEGIN
            Update tbl_group set description = @value where idgroup = @idgroup
        END

        IF @field = 'status'
        BEGIN
            Update tbl_group set status = @value where idgroup = @idgroup
        END
END

GO
GRANT EXECUTE ON SCHEMA::dbo TO appMock
GO
