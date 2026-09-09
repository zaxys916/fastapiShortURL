import bcrypt


class PasslibHelper:

    @staticmethod
    def hash_password(password: str) -> str:
        """对密码进行 bcrypt 加密"""
        return bcrypt.hashpw(
            password.encode("utf-8"), bcrypt.gensalt()
        ).decode("utf-8")

    @staticmethod
    def verify_password(plain_password: str, hashed_password: str) -> bool:
        """校验明文密码与 bcrypt 哈希是否匹配"""
        try:
            return bcrypt.checkpw(
                plain_password.encode("utf-8"), hashed_password.encode("utf-8")
            )
        except ValueError:
            # hashed_password 不是合法的 bcrypt 哈希时，直接判定为不匹配
            return False


if __name__ == '__main__':
    h = PasslibHelper.hash_password("123456")
    print(h)
    print(PasslibHelper.verify_password("123456", h))
