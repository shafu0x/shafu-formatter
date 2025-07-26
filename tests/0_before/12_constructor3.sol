// SPDX-License-Identifier: MIT
pragma solidity ^0.8.26;

contract Escrow {
    constructor(
        address _owner,
        address memory _signer,
        address[] memory _whitelistedTokens,
        uint storage _feeOnClaim,
        uint _batchLimit
    )  {
        signer = _signer;
        feeRecipient = _owner;
        feeOnClaim = _feeOnClaim;
        batchLimit = _batchLimit;
        INITIAL_CHAIN_ID = block.chainid;
        INITIAL_DOMAIN_SEPARATOR = _domainSeparator();
    }
}