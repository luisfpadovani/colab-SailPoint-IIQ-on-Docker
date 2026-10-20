USE appMock
GO
SET NOCOUNT ON;
-- Removing Administrator from one user must not remove it from another.
INSERT INTO dbo.tbl_user_group(iduser,idgroup) VALUES(2,1);
DECLARE @existingName nvarchar(200)=(SELECT name FROM dbo.tbl_user WHERE login='00000001');
EXEC dbo.UPDATE_USER '00000001', 'name', @existingName, '', 'Administrator';
IF EXISTS(SELECT 1 FROM dbo.tbl_user_group WHERE iduser=1 AND idgroup=1)
    THROW 51001, 'Target membership was not removed', 1;
IF NOT EXISTS(SELECT 1 FROM dbo.tbl_user_group WHERE iduser=2 AND idgroup=1)
    THROW 51002, 'Another user lost their membership', 1;
-- Duplicate name and duplicate login must stop without adding rows or memberships.
DECLARE @users int=(SELECT COUNT(*) FROM dbo.tbl_user);
DECLARE @members int=(SELECT COUNT(*) FROM dbo.tbl_user_group);
DECLARE @caught bit=0;
BEGIN TRY
    EXEC dbo.INSERT_USER @existingName, '99999999', 'Audit';
END TRY
BEGIN CATCH
    IF ERROR_NUMBER() <> 50001 THROW;
    SET @caught=1;
END CATCH;
IF @caught=0 THROW 51003, 'Duplicate name accepted', 1;
SET @caught=0;
BEGIN TRY
    EXEC dbo.INSERT_USER 'Another Fictional Identity', '00000001', 'Audit';
END TRY
BEGIN CATCH
    IF ERROR_NUMBER() <> 50001 THROW;
    SET @caught=1;
END CATCH;
IF @caught=0 THROW 51004, 'Duplicate login accepted', 1;
IF @users<>(SELECT COUNT(*) FROM dbo.tbl_user) OR @members<>(SELECT COUNT(*) FROM dbo.tbl_user_group)
    THROW 51005, 'Duplicate insertion changed data', 1;
EXEC dbo.INSERT_USER 'Runtime Regression', '99999999', 'Audit';
DECLARE @password nvarchar(200)=CONVERT(nvarchar(200),CRYPT_GEN_RANDOM(32),2);
EXEC dbo.UPDATE_USER '99999999', 'password', @password, '', '';
IF NOT EXISTS(SELECT 1 FROM dbo.tbl_user WHERE login='99999999' AND DATALENGTH(password_salt)=32 AND DATALENGTH(password_hash)=64
    AND password_hash=HASHBYTES('SHA2_512',password_salt+CONVERT(varbinary(max),@password)))
    THROW 51006, 'Password hash mismatch', 1;
IF EXISTS(SELECT password_salt FROM dbo.tbl_user GROUP BY password_salt HAVING COUNT(*)>1)
    THROW 51007, 'Repeated salt', 1;
IF HAS_PERMS_BY_NAME('dbo.tbl_user','OBJECT','SELECT')<>1
    THROW 51008, 'Admin cannot inspect fixture', 1;
PRINT 'PASS: target-only deletion, duplicate checks, salted hashes';
GO
