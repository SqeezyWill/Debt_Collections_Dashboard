from burpsuite.definitions import DEFINITIONS
from burpsuite.exceptions import IssueTypeIdError


class BurpSuiteIssueDefinition:
    """ Burp Suite issue class """

    def __init__(self, issue_type_id, name, description, remediation, references, vulnerability_classifications):
        self.__issue_type_id = issue_type_id
        self.__name = name
        self.__description = description
        self.__remediation = remediation
        self.__references = references
        self.__vulnerability_classifications = vulnerability_classifications

    def __repr__(self):
        return "<BurpSuiteIssueDefinition.{}>".format(self.__issue_type_id)

    @property
    def issue_type_id(self):
        return self.__issue_type_id

    @property
    def name(self):
        return self.__name

    @property
    def description(self):
        return self.__description

    @property
    def remediation(self):
        return self.__remediation

    @property
    def references(self):
        return self.__references

    @property
    def vulnerability_classifications(self):
        return self.__vulnerability_classifications

    def to_dict(self):
        """ Returns a dictionary representation of the object """
        return dict(
            issue_type_id=self.__issue_type_id,
            name=self.__name,
            description=self.__description,
            remediation=self.__remediation,
            references=self.__references,
            vulnerability_classifications=self.__vulnerability_classifications
        )


def get_issue_type_ids():
    """ Returns a list of issue_type_ids """
    return [i["issue_type_id"] for i in DEFINITIONS]


def get_definitions():
    """ Returns all definitions

    Returns:
        list: A list of dictionaries
    """
    return DEFINITIONS


def get_definition(issue_type_id):

    """ Returns a Burp Suite issue definition

    Args:
        issue_type_id (str/int): The issue type ID
    Returns:
        BurpSuiteIssueDefinition (class)
    """

    if not isinstance(issue_type_id, str) and not isinstance(issue_type_id, int):
        raise ValueError("issue_type_id must be str or int, not {}".format(type(issue_type_id)))

    if issue_type_id not in get_issue_type_ids():
        raise IssueTypeIdError("No matching result for {}".format(issue_type_id))

    for d in DEFINITIONS:
        if d["issue_type_id"] == str(issue_type_id):
            match = d

            return BurpSuiteIssueDefinition(
                issue_type_id=match.get("issue_type_id", None),
                name=match.get("name", None),
                description=match.get("description", None),
                remediation=match.get("remediation", None),
                references=match.get("references", None),
                vulnerability_classifications=match.get("vulnerability_classifications", None),
            )


if __name__ == "__main__":
    definition = get_definition("2097920")
    print(definition)
    print(definition.to_dict())