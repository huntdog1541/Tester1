from keystone import *
import sys
from flask import *
import json

app = Flask(__name__)

ks_arch_dict = {
    "X86": KS_ARCH_X86,
    "ARM": KS_ARCH_ARM,
    "ARM64": KS_ARCH_ARM64,
    "EVM": KS_ARCH_EVM,
    "MIPS": KS_ARCH_MIPS,
    "PPC": KS_ARCH_PPC,
    "SPARC": KS_ARCH_SPARC
}

ks_mode_dict = {
    "X16": KS_MODE_16,
    "X32": KS_MODE_32,
    "X64": KS_MODE_64,
    "ARM": KS_MODE_ARM,
    "THUMB": KS_MODE_THUMB,
    "MICRO": KS_MODE_MICRO,
    "MIPS3": KS_MODE_MIPS3,
    "MIPS32R6": KS_MODE_MIPS32R6,
    "V8": KS_MODE_V8,
    "V9": KS_MODE_V9,
    "QPX": KS_MODE_QPX
}

ks_endian_dict = {
    "LITTLE": KS_MODE_LITTLE_ENDIAN,
    "BIG": KS_MODE_BIG_ENDIAN
}


def get_arch(arch_str):
    return ks_arch_dict[arch_str]


def get_mode(mode_str):
    return ks_mode_dict[mode_str]


def get_endian(endian_str):
    return ks_endian_dict[endian_str]


def get_arch_str(arch_val):
    for x in ks_arch_dict:
        if arch_val == ks_arch_dict[x]:
            return x
    return None


def get_mode_str(mode_val):
    for x in ks_mode_dict:
        if mode_val == ks_mode_dict[x]:
            return x
    return None


def get_endian_str(endian_val):
    for x in ks_endian_dict:
        if endian_val == ks_endian_dict[x]:
            return x
    return None


def keystone_execute(arch, mode, code, end=KS_MODE_LITTLE_ENDIAN, syntax=0):
    ks = Ks(arch, mode)
    results = Result()
    if syntax != 0:
        ks.syntax = syntax

    machine_code = []

    results.arch = arch
    results.mode = mode
    results.end = end

    for i in code:
        try:
            encoding, count = ks.asm(i)
        except KsError as e:
            print('Error on line: %s' % i)
            print('Message: %s ' % e.message)
            print(KsError)
            error = KeystoneError(e.errno, i, e.stat_count)
            # raise error
        else:
            temp = []
            for j in encoding:
                temp.append(j)
            machine_code.append(temp)

            iterator = 0
            for a in code:
                print("Code Size: ")
                print("%s = [" % a, end='')
            for b in machine_code[iterator]:
                print("%02x " % b, end='')
            print("]")
            iterator += 1

            results.code = machine_code
            results.instructions = code

    return results


@app.route('/')
def status():
    return 'Up and Running'


class Validation:
    arch_err = False
    arch = None
    mode_err = False
    mode = None
    end_err = False
    end = None
    instructions_err = False
    instructions = None


class Result:
    arch = None
    mode = None
    end = None
    instructions = None
    code = None


class KeystoneError(KsError):
    def __init__(self, errno, errorLine, count=None):
        super().__init__(errno, count)
        self.errorLine = errorLine

    def __str__(self):
        return "Error: %s on line: %s " % self.message, self.errorLine


@app.route('/api', methods=['GET', 'POST'])
def get_assembly():
    json_request = request.get_json()
    result, val = validate_input(json_request)

    if result:
        try:
            code = keystone_execute(val.arch, val.mode, val.instructions, val.end)
            # return pretty_result(code)
            answer = clean_results(code)
            return json.dumps(answer.__dict__)
            # return json.dumps(code.__dict__)
        except KeystoneError as error:
            print('Error on line: %s ' % error.__str__())
    else:
        return 'Get Assembly'


def pretty_result(res):
    strg = ''
    arch = get_arch_str(res.arch)
    strg += 'Architecture: %s ' % arch
    mode = get_mode_str(res.mode)
    strg += 'Mode: %s ' % mode
    strg += 'Instructions: [ '
    for a in res.instructions:
        strg += '\'%s\', ' % a
    strg += ' ] '
    strg += 'Machine Code: [ '
    for i in res.code:
        strg += ' [ '
        for j in i:
            strg += '%s, ' % hex(j)
        strg += ' ] '
    strg += ' ] '
    return strg


def clean_results(res):
    answer = Result()
    answer.arch = get_arch_str(res.arch)
    answer.mode = get_mode_str(res.mode)
    answer.instructions = res.instructions
    code = []
    for i in res.code:
        temp = []
        for j in i:
            temp.append('%s' % hex(j))
        code.append(temp)
    answer.code = code
    return answer


def validate_input(json):
    val = Validation()
    val.arch, val.arch_err = validate_architecture(json)
    val.mode, val.mode_err = validate_mode(json)
    val.end, val.end_err = validate_endian(json)
    val.instructions, val.instructions_err = validate_instructions(json)

    if val.arch_err or val.mode_err or val.instructions_err:
        print_error(val)
        return False
    else:
        return True, val


def validate_architecture(json):
    if json.get('architecture') is not None:
        print('Arch: %s' % json.get('architecture'), file=sys.stderr)
        try:
            return get_arch(json.get('architecture').upper()), False
        except KeyError:
            return f"ERROR: {json.get('architecture')} is not a supported architecture", True
    else:
        return 'ERROR: architecture is none, architecture is required', True


def validate_endian(json):
    if json.get('endian') is not None:
        print('Endian: %s' % json.get('endian'), file=sys.stderr)
        try:
            return get_endian(json.get('endian').upper()), False
        except KeyError:
            return f"ERROR: {json.get('endian')} is not a supported endian", True
    else:
        return KS_MODE_LITTLE_ENDIAN, False  # Little Endian is default


def validate_mode(json):
    if json.get('mode') is not None:
        print('Mode: %s' % json.get('mode'), file=sys.stderr)
        try:
            return get_mode(json.get('mode').upper()), False
        except KeyError:
            return f"ERROR: {json.get('mode')} is not supported mode", True
    else:
        return f"ERROR: mode is none, mode is required", True


def validate_instructions(json):
    if json.get('instructions') is not None:
        print('Instructions: %s ' % json.get('instructions'))
        return json.get('instructions'), False
    else:
        return f"ERROR: instructions is none, instructions are required", True


def print_error(val):
    message = ""
    if val.arch_err:
        message += val.arch + '\n'
    if val.mode_err:
        message += val.mode + '\n'
    if val.instructions_err:
        message += val.instructions + '\n'

    return message


if __name__ == '__main__':
    keystone_execute(KS_ARCH_X86, KS_MODE_16, b"add eax, ecx")
