// SPDX-License-Identifier: MIT
pragma solidity ^0.8.26;

contract Escrow {
    function fund()  {
        require(!account.exists,                            Errors.REPO_ALREADY_INITIALIZED);
        require(admins.length         >  0,                 Errors.INVALID_AMOUNT);
        require(admins.length         <= batchLimit,        Errors.BATCH_LIMIT_EXCEEDED);
        require(block.timestamp       <= signatureDeadline, Errors.SIGNATURE_EXPIRED);
        require(_distributions.length >  0,                 Errors.EMPTY_ARRAY);
        require(_distributions.length <= batchLimit,        Errors.BATCH_LIMIT_EXCEEDED);
        // do things

        require(distribution.exists,                                      Errors.INVALID_DISTRIBUTION_ID);
        require(distribution.status    == DistributionStatus.Distributed, Errors.ALREADY_CLAIMED);
        require(distribution.recipient == msg.sender,                     Errors.INVALID_RECIPIENT);
    }
}